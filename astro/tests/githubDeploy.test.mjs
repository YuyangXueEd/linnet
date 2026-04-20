import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildGitHubCallPreview,
  deployGeneratedConfig,
  parseRepoInput,
  utf8ToBase64,
} from '../src/components/wizard/githubDeploy.js';

function jsonResponse(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 404 ? 'Not Found' : 'OK',
    headers: {
      get(name) {
        return name.toLowerCase() === 'content-type' ? 'application/json; charset=utf-8' : null;
      },
    },
    async json() {
      return body;
    },
  };
}

test('parseRepoInput accepts slug and GitHub URL forms', () => {
  assert.deepEqual(parseRepoInput('owner/repo'), { owner: 'owner', repo: 'repo' });
  assert.deepEqual(parseRepoInput('https://github.com/openai/linnet.git'), { owner: 'openai', repo: 'linnet' });
  assert.equal(parseRepoInput('not a repo'), null);
});

test('buildGitHubCallPreview includes contents and secrets endpoints', () => {
  const preview = buildGitHubCallPreview({
    owner: 'openai',
    repo: 'linnet',
    files: [{ path: 'config/sources.yaml', body: 'hello' }],
    secrets: [{ name: 'OPENROUTER_API_KEY', value: 'secret' }],
  });

  assert.deepEqual(preview, [
    'GET /repos/openai/linnet',
    'GET /repos/openai/linnet/contents/config/sources.yaml?ref=<default_branch>',
    'PUT /repos/openai/linnet/contents/config/sources.yaml',
    'GET /repos/openai/linnet/actions/secrets/public-key',
    'PUT /repos/openai/linnet/actions/secrets/OPENROUTER_API_KEY',
    'POST /repos/openai/linnet/actions/workflows/daily.yml/dispatches',
  ]);
});

test('buildGitHubCallPreview supports non-OpenRouter secret names', () => {
  const preview = buildGitHubCallPreview({
    owner: 'openai',
    repo: 'linnet',
    files: [{ path: 'config/sources.yaml', body: 'hello' }],
    secrets: [{ name: 'OPENAI_API_KEY', value: 'secret' }],
  });

  assert.equal(
    preview.at(-2),
    'PUT /repos/openai/linnet/actions/secrets/OPENAI_API_KEY',
  );
  assert.equal(
    preview.at(-1),
    'POST /repos/openai/linnet/actions/workflows/daily.yml/dispatches',
  );
});

test('deployGeneratedConfig updates files and secrets serially', async () => {
  const calls = [];
  const responses = [
    jsonResponse(200, { default_branch: 'main', html_url: 'https://github.com/openai/linnet' }),
    jsonResponse(200, { sha: 'existing-sha' }),
    jsonResponse(200, { content: null, commit: { sha: 'commit-sha' } }),
    jsonResponse(200, { key: 'PUBLIC_KEY', key_id: 'KEY_ID' }),
    jsonResponse(201, {}),
  ];

  const fetchImpl = async (url, init = {}) => {
    calls.push({ url, init });
    const response = responses.shift();
    assert.ok(response, `Unexpected extra fetch call for ${url}`);
    return response;
  };

  const result = await deployGeneratedConfig({
    owner: 'openai',
    repo: 'linnet',
    token: 'github_pat_123',
    files: [{ path: 'config/sources.yaml', body: 'language: "en"\n' }],
    secrets: [{ name: 'OPENROUTER_API_KEY', value: 'sk-or-123' }],
    fetchImpl,
    encryptSecretImpl: async () => 'encrypted-secret',
    commitMessage: 'test commit',
  });

  assert.equal(result.defaultBranch, 'main');
  assert.equal(result.htmlUrl, 'https://github.com/openai/linnet');
  assert.deepEqual(result.committedPaths, ['config/sources.yaml']);
  assert.deepEqual(result.writtenSecrets, ['OPENROUTER_API_KEY']);

  assert.equal(calls.length, 5);
  assert.match(calls[1].url, /contents\/config\/sources\.yaml\?ref=main$/);
  assert.match(calls[2].url, /contents\/config\/sources\.yaml$/);

  const putFileBody = JSON.parse(calls[2].init.body);
  assert.equal(putFileBody.message, 'test commit');
  assert.equal(putFileBody.branch, 'main');
  assert.equal(putFileBody.sha, 'existing-sha');
  assert.equal(putFileBody.content, utf8ToBase64('language: "en"\n'));

  const putSecretBody = JSON.parse(calls[4].init.body);
  assert.deepEqual(putSecretBody, {
    encrypted_value: 'encrypted-secret',
    key_id: 'KEY_ID',
  });
});
