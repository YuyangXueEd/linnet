// @ts-check

/**
 * @typedef {{ path: string, body: string }} DeployFile
 * @typedef {{ name: string, value: string }} DeploySecret
 * @typedef {{ owner: string, repo: string }} RepoRef
 * @typedef {{ defaultBranch: string, htmlUrl: string, committedPaths: string[], writtenSecrets: string[] }} DeployResult
 */

const API_BASE = 'https://api.github.com';
const API_VERSION = '2022-11-28';
const SODIUM_ESM_URL = 'https://esm.sh/libsodium-wrappers@0.7.15';

/** @type {Promise<any> | undefined} */
let sodiumPromise;

/**
 * @param {string} input
 * @returns {RepoRef | null}
 */
export function parseRepoInput(input) {
  const trimmed = input.trim().replace(/\.git$/i, '');
  if (!trimmed) return null;

  const fromUrl = trimmed.match(/github\.com\/([^/]+)\/([^/]+)/i);
  const fromSlug = trimmed.match(/^([^/\s]+)\/([^/\s]+)$/);
  const match = fromUrl ?? fromSlug;
  if (!match) return null;

  return {
    owner: decodeURIComponent(match[1]),
    repo: decodeURIComponent(match[2]),
  };
}

/**
 * @param {{
 *   owner: string,
 *   repo: string,
 *   files: DeployFile[],
 *   secrets: DeploySecret[],
 *   autoEnableActions?: boolean,
 *   workflowsToEnable?: string[]
 * }} plan
 * @returns {string[]}
 */
export function buildGitHubCallPreview(plan) {
  const lines = [
    `GET /repos/${plan.owner}/${plan.repo}`,
  ];

  for (const file of plan.files) {
    lines.push(`GET /repos/${plan.owner}/${plan.repo}/contents/${file.path}?ref=<default_branch>`);
    lines.push(`PUT /repos/${plan.owner}/${plan.repo}/contents/${file.path}`);
  }

  if (plan.secrets.length) {
    lines.push(`GET /repos/${plan.owner}/${plan.repo}/actions/secrets/public-key`);
    for (const secret of plan.secrets) {
      lines.push(`PUT /repos/${plan.owner}/${plan.repo}/actions/secrets/${secret.name}`);
    }
  }

  if (plan.autoEnableActions) {
    lines.push(`PUT /repos/${plan.owner}/${plan.repo}/actions/permissions`);
    for (const workflowId of plan.workflowsToEnable ?? []) {
      lines.push(`PUT /repos/${plan.owner}/${plan.repo}/actions/workflows/${workflowId}/enable`);
    }
  }

  lines.push(`POST /repos/${plan.owner}/${plan.repo}/actions/workflows/daily.yml/dispatches`);

  return lines;
}

/**
 * @param {string} input
 * @returns {string}
 */
export function utf8ToBase64(input) {
  const bytes = new TextEncoder().encode(input);
  if (typeof Buffer !== 'undefined') {
    return Buffer.from(bytes).toString('base64');
  }

  let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

/**
 * @param {string} token
 * @returns {Record<string, string>}
 */
export function githubHeaders(token) {
  return {
    Accept: 'application/vnd.github+json',
    Authorization: `Bearer ${token}`,
    'X-GitHub-Api-Version': API_VERSION,
    'Content-Type': 'application/json',
  };
}

/**
 * @param {string} path
 * @returns {string}
 */
function encodeContentPath(path) {
  return path.split('/').map((part) => encodeURIComponent(part)).join('/');
}

/**
 * @param {ReturnType<typeof fetch>} responsePromise
 */
async function parseError(responsePromise) {
  const response = await responsePromise;
  let message = `${response.status} ${response.statusText}`;
  try {
    const data = await response.json();
    if (typeof data?.message === 'string') message = data.message;
  } catch {
    // Ignore JSON parsing failure and fall back to status text.
  }
  return new Error(message);
}

/**
 * @param {string} token
 * @param {string} path
 * @param {RequestInit} [init]
 * @param {typeof fetch} [fetchImpl]
 */
async function githubRequest(token, path, init = {}, fetchImpl = fetch) {
  const response = await fetchImpl(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...githubHeaders(token),
      ...(init.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw await parseError(Promise.resolve(response));
  }

  if (response.status === 204) return null;
  const contentType = response.headers.get('content-type') ?? '';
  if (!contentType.includes('application/json')) return null;
  return response.json();
}

/**
 * @returns {Promise<any>}
 */
async function loadSodium() {
  if (!sodiumPromise) sodiumPromise = import(SODIUM_ESM_URL);
  const mod = await sodiumPromise;
  const sodium = mod.default || mod;
  await sodium.ready;
  return sodium;
}

/**
 * @param {string} value
 * @param {string} base64PublicKey
 * @returns {Promise<string>}
 */
export async function encryptSecretForGitHub(value, base64PublicKey) {
  const sodium = await loadSodium();
  const publicKey = sodium.from_base64(base64PublicKey, sodium.base64_variants.ORIGINAL);
  const encrypted = sodium.crypto_box_seal(value, publicKey);
  return sodium.to_base64(encrypted, sodium.base64_variants.ORIGINAL);
}

/**
 * @param {{
 *   owner: string,
 *   repo: string,
 *   token: string,
 *   files: DeployFile[],
 *   secrets: DeploySecret[],
 *   commitMessage?: string,
 *   fetchImpl?: typeof fetch,
 *   encryptSecretImpl?: (value: string, key: string) => Promise<string>
 * }} plan
 * @returns {Promise<DeployResult>}
 */
export async function deployGeneratedConfig(plan) {
  const {
    owner,
    repo,
    token,
    files,
    secrets,
    commitMessage = 'chore: configure Linnet via setup wizard',
    fetchImpl = fetch,
    encryptSecretImpl = encryptSecretForGitHub,
  } = plan;

  const repoInfo = await githubRequest(token, `/repos/${owner}/${repo}`, {}, fetchImpl);
  const defaultBranch = repoInfo?.default_branch ?? 'main';
  const htmlUrl = repoInfo?.html_url ?? `https://github.com/${owner}/${repo}`;

  /** @type {string[]} */
  const committedPaths = [];
  for (const file of files) {
    const encodedPath = encodeContentPath(file.path);
    let existingSha = null;

    try {
      const existing = await githubRequest(
        token,
        `/repos/${owner}/${repo}/contents/${encodedPath}?ref=${encodeURIComponent(defaultBranch)}`,
        {},
        fetchImpl,
      );
      existingSha = existing?.sha ?? null;
    } catch (error) {
      if (!(error instanceof Error) || !error.message.includes('404')) {
        throw error;
      }
    }

    await githubRequest(
      token,
      `/repos/${owner}/${repo}/contents/${encodedPath}`,
      {
        method: 'PUT',
        body: JSON.stringify({
          message: commitMessage,
          content: utf8ToBase64(file.body),
          branch: defaultBranch,
          ...(existingSha ? { sha: existingSha } : {}),
        }),
      },
      fetchImpl,
    );

    committedPaths.push(file.path);
  }

  /** @type {string[]} */
  const writtenSecrets = [];
  if (secrets.length) {
    const publicKey = await githubRequest(
      token,
      `/repos/${owner}/${repo}/actions/secrets/public-key`,
      {},
      fetchImpl,
    );

    for (const secret of secrets) {
      const encryptedValue = await encryptSecretImpl(secret.value, publicKey.key);
      await githubRequest(
        token,
        `/repos/${owner}/${repo}/actions/secrets/${encodeURIComponent(secret.name)}`,
        {
          method: 'PUT',
          body: JSON.stringify({
            encrypted_value: encryptedValue,
            key_id: publicKey.key_id,
          }),
        },
        fetchImpl,
      );
      writtenSecrets.push(secret.name);
    }
  }

  return {
    defaultBranch,
    htmlUrl,
    committedPaths,
    writtenSecrets,
  };
}

/**
 * @param {string} token
 * @param {string} owner
 * @param {string} repo
 * @param {typeof fetch} [fetchImpl]
 */
export async function setRepositoryActionsEnabled(token, owner, repo, fetchImpl = fetch) {
  return githubRequest(
    token,
    `/repos/${owner}/${repo}/actions/permissions`,
    {
      method: 'PUT',
      body: JSON.stringify({ enabled: true }),
    },
    fetchImpl,
  );
}

/**
 * @param {string} token
 * @param {string} owner
 * @param {string} repo
 * @param {string} workflowId
 * @param {typeof fetch} [fetchImpl]
 */
export async function enableWorkflow(token, owner, repo, workflowId, fetchImpl = fetch) {
  return githubRequest(
    token,
    `/repos/${owner}/${repo}/actions/workflows/${encodeURIComponent(workflowId)}/enable`,
    {
      method: 'PUT',
    },
    fetchImpl,
  );
}

/**
 * @param {string} token
 * @param {string} owner
 * @param {string} repo
 * @param {string} workflowId
 * @param {string} [ref]
 * @param {typeof fetch} [fetchImpl]
 */
export async function triggerWorkflowDispatch(token, owner, repo, workflowId, ref = 'main', fetchImpl = fetch) {
  return githubRequest(
    token,
    `/repos/${owner}/${repo}/actions/workflows/${workflowId}/dispatches`,
    {
      method: 'POST',
      body: JSON.stringify({ ref }),
    },
    fetchImpl,
  );
}
