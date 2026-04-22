import assert from 'node:assert/strict';
import { generateKeyPairSync } from 'node:crypto';
import test from 'node:test';
import { buildDefaultPagesUrl, deployWithInstallation, utf8ToBase64 } from '../src/deploy';
import type { GitHubAppConfig } from '../src/github';

function jsonResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'content-type': 'application/json; charset=utf-8',
    },
  });
}

const keyPair = generateKeyPairSync('rsa', {
  modulusLength: 2048,
  privateKeyEncoding: {
    format: 'pem',
    type: 'pkcs1',
  },
  publicKeyEncoding: {
    format: 'pem',
    type: 'spki',
  },
});

const config: GitHubAppConfig = {
  slug: 'linnet',
  appId: '1',
  clientId: 'Iv1.test',
  clientSecret: 'secret',
  privateKey: keyPair.privateKey,
  jwtIssuer: 'Iv1.test',
  jwtIssuerSource: 'client_id',
};

const repositoryPublicKey = Buffer.alloc(32, 7).toString('base64');

test('buildDefaultPagesUrl handles project and user pages', () => {
  assert.equal(buildDefaultPagesUrl('octocat', 'briefing'), 'https://octocat.github.io/briefing/');
  assert.equal(buildDefaultPagesUrl('octocat', 'octocat.github.io'), 'https://octocat.github.io/');
});

test('utf8ToBase64 encodes utf8 text', () => {
  assert.equal(utf8ToBase64('language: "en"\n'), 'bGFuZ3VhZ2U6ICJlbiIK');
});

test('deployWithInstallation scopes token and performs repo writes, secrets, actions, pages, and dispatch', async () => {
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  const responses = [
    jsonResponse(201, { token: 'installation-token', expires_at: '2026-04-22T10:00:00Z' }),
    jsonResponse(200, {
      id: 1,
      name: 'briefing',
      full_name: 'octocat/briefing',
      default_branch: 'main',
      html_url: 'https://github.com/octocat/briefing',
    }),
    jsonResponse(404, { message: 'Not Found' }),
    jsonResponse(200, {}),
    jsonResponse(200, { key: repositoryPublicKey, key_id: 'KEY_ID' }),
    jsonResponse(201, {}),
    new Response(null, { status: 204 }),
    new Response(null, { status: 204 }),
    new Response(null, { status: 204 }),
    new Response(null, { status: 204 }),
    new Response(null, { status: 204 }),
    jsonResponse(404, { message: 'Not Found' }),
    jsonResponse(201, {
      html_url: 'https://octocat.github.io/briefing/',
      build_type: 'workflow',
      source: { branch: 'main', path: '/' },
    }),
    new Response(null, { status: 204 }),
  ];

  const fetchImpl: typeof fetch = async (url, init) => {
    calls.push({ url: String(url), init });
    const response = responses.shift();
    assert.ok(response, `Unexpected extra fetch call for ${url}`);
    return response;
  };

  const result = await deployWithInstallation(
    config,
    {
      installationId: 77,
      repo: { owner: 'octocat', repo: 'briefing' },
      files: [{ path: 'config/sources.yaml', body: 'language: "en"\n' }],
      secrets: [{ name: 'OPENROUTER_API_KEY', value: 'sk-or-123' }],
    },
    fetchImpl,
  );

  assert.equal(result.repo.defaultBranch, 'main');
  assert.deepEqual(result.committedPaths, ['config/sources.yaml']);
  assert.deepEqual(result.writtenSecrets, ['OPENROUTER_API_KEY']);
  assert.equal(result.actions.enabled, true);
  assert.deepEqual(result.actions.enabledWorkflows, ['daily.yml', 'weekly.yml', 'monthly.yml', 'pages.yml']);
  assert.equal(result.pages.status, 'created');
  assert.equal(result.workflowDispatch.workflowId, 'daily.yml');
  assert.equal(result.workflowDispatch.ref, 'main');

  assert.equal(calls.length, 14);
  assert.match(calls[0].url, /\/app\/installations\/77\/access_tokens$/);
  assert.match(calls[1].url, /\/repos\/octocat\/briefing$/);
  assert.match(calls[2].url, /contents\/config\/sources\.yaml\?ref=main$/);
  assert.match(calls[3].url, /contents\/config\/sources\.yaml$/);
  assert.match(calls[4].url, /actions\/secrets\/public-key$/);
  assert.match(calls[5].url, /actions\/secrets\/OPENROUTER_API_KEY$/);
  assert.match(calls[12].url, /\/repos\/octocat\/briefing\/pages$/);
  assert.match(calls[13].url, /actions\/workflows\/daily\.yml\/dispatches$/);

  const tokenBody = JSON.parse(String(calls[0].init?.body));
  assert.deepEqual(tokenBody, { repositories: ['briefing'] });

  const putFileBody = JSON.parse(String(calls[3].init?.body));
  assert.equal(putFileBody.content, 'bGFuZ3VhZ2U6ICJlbiIK');

  const putSecretBody = JSON.parse(String(calls[5].init?.body));
  assert.equal(putSecretBody.key_id, 'KEY_ID');
  assert.equal(typeof putSecretBody.encrypted_value, 'string');
  assert.notEqual(putSecretBody.encrypted_value, '');
  assert.notEqual(putSecretBody.encrypted_value, 'sk-or-123');

  const pagesBody = JSON.parse(String(calls[12].init?.body));
  assert.deepEqual(pagesBody, {
    build_type: 'workflow',
    source: {
      branch: 'main',
      path: '/',
    },
  });

  const dispatchBody = JSON.parse(String(calls[13].init?.body));
  assert.deepEqual(dispatchBody, { ref: 'main' });
});
