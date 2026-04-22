import { GitHubApiError, GitHubAppConfig, createInstallationAccessToken } from './github';

const GITHUB_API_BASE = 'https://api.github.com';
const GITHUB_API_VERSION = '2026-03-10';
const DEFAULT_COMMIT_MESSAGE = 'chore: configure Linnet via setup bridge';
const DEFAULT_WORKFLOWS = ['daily.yml', 'weekly.yml', 'monthly.yml', 'pages.yml'];

export type DeployFile = {
  path: string;
  body: string;
};

export type DeploySecret = {
  name: string;
  value: string;
};

export type RepoRef = {
  owner: string;
  repo: string;
};

export type DeployRequest = {
  installationId: number;
  repo: RepoRef;
  files: DeployFile[];
  secrets: DeploySecret[];
  commitMessage?: string;
  autoEnableActions?: boolean;
  workflowsToEnable?: string[];
  configurePages?: boolean;
  pagesSourcePath?: '/' | '/docs';
  triggerWorkflowId?: string;
  triggerWorkflowRef?: string;
};

export type DeployResult = {
  repo: {
    owner: string;
    repo: string;
    defaultBranch: string;
    htmlUrl: string;
  };
  committedPaths: string[];
  writtenSecrets: string[];
  actions: {
    attempted: boolean;
    enabled: boolean;
    enabledWorkflows: string[];
  };
  pages: {
    attempted: boolean;
    status: 'created' | 'updated' | 'unchanged' | 'skipped';
    htmlUrl: string | null;
    sourceBranch: string | null;
    sourcePath: string | null;
    buildType: string | null;
  };
  workflowDispatch: {
    attempted: boolean;
    workflowId: string | null;
    ref: string | null;
    triggered: boolean;
  };
};

type RepoInfo = {
  id: number;
  name: string;
  full_name: string;
  default_branch?: string;
  html_url?: string;
};

type RepoContent = {
  sha?: string;
};

type RepoSecretPublicKey = {
  key: string;
  key_id: string;
};

type PagesSite = {
  html_url?: string;
  build_type?: string;
  source?: {
    branch?: string;
    path?: string;
  };
};

type InstallationAccessTokenResponse = {
  token: string;
  expires_at: string;
  permissions?: Record<string, string>;
};

function encodeContentPath(path: string): string {
  return path.split('/').map((part) => encodeURIComponent(part)).join('/');
}

function githubHeaders(token: string): Record<string, string> {
  return {
    Accept: 'application/vnd.github+json',
    Authorization: `Bearer ${token}`,
    'User-Agent': 'linnet-setup-bridge',
    'X-GitHub-Api-Version': GITHUB_API_VERSION,
    'Content-Type': 'application/json',
  };
}

async function parseGitHubError(response: Response): Promise<GitHubApiError> {
  const text = await response.text();
  let details: unknown = null;
  try {
    details = text ? JSON.parse(text) : null;
  } catch {
    details = text || null;
  }

  let message = `${response.status} ${response.statusText}`;
  if (details && typeof details === 'object' && details !== null && 'message' in details) {
    const detailMessage = (details as { message?: unknown }).message;
    if (typeof detailMessage === 'string' && detailMessage) message = detailMessage;
  }

  return new GitHubApiError(message, response.status, details);
}

async function githubInstallationRequest<T>(
  token: string,
  path: string,
  init: RequestInit = {},
  fetchImpl: typeof fetch = fetch,
): Promise<T | null> {
  const response = await fetchImpl(`${GITHUB_API_BASE}${path}`, {
    ...init,
    headers: {
      ...githubHeaders(token),
      ...(init.headers ?? {}),
    },
  });

  if (!response.ok) throw await parseGitHubError(response);
  if (response.status === 204) return null;
  const contentType = response.headers.get('content-type') ?? '';
  if (!contentType.includes('application/json')) return null;
  return (await response.json()) as T;
}

export function utf8ToBase64(input: string): string {
  return Buffer.from(new TextEncoder().encode(input)).toString('base64');
}

export function buildDefaultPagesUrl(owner: string, repo: string): string {
  const isUserSiteRepo = repo.toLowerCase() === `${owner.toLowerCase()}.github.io`;
  return `https://${owner}.github.io${isUserSiteRepo ? '/' : `/${repo}/`}`;
}

async function encryptSecretForGitHub(value: string, base64PublicKey: string): Promise<string> {
  const sodium = (await import('libsodium-wrappers')).default;
  await sodium.ready;
  const publicKey = sodium.from_base64(base64PublicKey, sodium.base64_variants.ORIGINAL);
  const encrypted = sodium.crypto_box_seal(value, publicKey);
  return sodium.to_base64(encrypted, sodium.base64_variants.ORIGINAL);
}

async function getScopedInstallationToken(
  config: GitHubAppConfig,
  installationId: number,
  repoName: string,
  fetchImpl: typeof fetch,
): Promise<InstallationAccessTokenResponse> {
  return createInstallationAccessToken(config, installationId, {
    repositories: [repoName],
  }, fetchImpl);
}

async function getRepository(
  token: string,
  repo: RepoRef,
  fetchImpl: typeof fetch,
): Promise<RepoInfo> {
  const data = await githubInstallationRequest<RepoInfo>(token, `/repos/${repo.owner}/${repo.repo}`, {}, fetchImpl);
  if (!data) throw new GitHubApiError('Repository metadata request returned no content', 500);
  return data;
}

async function upsertRepositoryFiles(
  token: string,
  repo: RepoRef,
  defaultBranch: string,
  files: DeployFile[],
  commitMessage: string,
  fetchImpl: typeof fetch,
): Promise<string[]> {
  const committedPaths: string[] = [];

  for (const file of files) {
    const encodedPath = encodeContentPath(file.path);
    let existingSha: string | null = null;

    try {
      const existing = await githubInstallationRequest<RepoContent>(
        token,
        `/repos/${repo.owner}/${repo.repo}/contents/${encodedPath}?ref=${encodeURIComponent(defaultBranch)}`,
        {},
        fetchImpl,
      );
      existingSha = existing?.sha ?? null;
    } catch (error) {
      if (!(error instanceof GitHubApiError) || error.status !== 404) throw error;
    }

    await githubInstallationRequest(
      token,
      `/repos/${repo.owner}/${repo.repo}/contents/${encodedPath}`,
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

  return committedPaths;
}

async function upsertRepositorySecrets(
  token: string,
  repo: RepoRef,
  secrets: DeploySecret[],
  fetchImpl: typeof fetch,
): Promise<string[]> {
  if (secrets.length === 0) return [];

  const publicKey = await githubInstallationRequest<RepoSecretPublicKey>(
    token,
    `/repos/${repo.owner}/${repo.repo}/actions/secrets/public-key`,
    {},
    fetchImpl,
  );
  if (!publicKey) throw new GitHubApiError('Repository secret public key request returned no content', 500);

  const writtenSecrets: string[] = [];
  for (const secret of secrets) {
    const encryptedValue = await encryptSecretForGitHub(secret.value, publicKey.key);
    await githubInstallationRequest(
      token,
      `/repos/${repo.owner}/${repo.repo}/actions/secrets/${encodeURIComponent(secret.name)}`,
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

  return writtenSecrets;
}

async function setRepositoryActionsEnabled(
  token: string,
  repo: RepoRef,
  fetchImpl: typeof fetch,
): Promise<void> {
  await githubInstallationRequest(
    token,
    `/repos/${repo.owner}/${repo.repo}/actions/permissions`,
    {
      method: 'PUT',
      body: JSON.stringify({ enabled: true }),
    },
    fetchImpl,
  );
}

async function enableWorkflow(
  token: string,
  repo: RepoRef,
  workflowId: string,
  fetchImpl: typeof fetch,
): Promise<void> {
  await githubInstallationRequest(
    token,
    `/repos/${repo.owner}/${repo.repo}/actions/workflows/${encodeURIComponent(workflowId)}/enable`,
    {
      method: 'PUT',
    },
    fetchImpl,
  );
}

async function ensurePagesSite(
  token: string,
  repo: RepoRef,
  defaultBranch: string,
  sourcePath: '/' | '/docs',
  fetchImpl: typeof fetch,
): Promise<DeployResult['pages']> {
  const body = {
    build_type: 'workflow',
    source: {
      branch: defaultBranch,
      path: sourcePath,
    },
  };

  try {
    const existing = await githubInstallationRequest<PagesSite>(
      token,
      `/repos/${repo.owner}/${repo.repo}/pages`,
      {},
      fetchImpl,
    );

    const isAlreadyConfigured =
      existing?.build_type === 'workflow' &&
      existing?.source?.branch === defaultBranch &&
      existing?.source?.path === sourcePath;

    if (isAlreadyConfigured) {
      return {
        attempted: true,
        status: 'unchanged',
        htmlUrl: existing?.html_url ?? buildDefaultPagesUrl(repo.owner, repo.repo),
        sourceBranch: existing?.source?.branch ?? defaultBranch,
        sourcePath: existing?.source?.path ?? sourcePath,
        buildType: existing?.build_type ?? 'workflow',
      };
    }

    await githubInstallationRequest(
      token,
      `/repos/${repo.owner}/${repo.repo}/pages`,
      {
        method: 'PUT',
        body: JSON.stringify(body),
      },
      fetchImpl,
    );

    return {
      attempted: true,
      status: 'updated',
      htmlUrl: existing?.html_url ?? buildDefaultPagesUrl(repo.owner, repo.repo),
      sourceBranch: defaultBranch,
      sourcePath,
      buildType: 'workflow',
    };
  } catch (error) {
    if (!(error instanceof GitHubApiError) || error.status !== 404) throw error;

    const created = await githubInstallationRequest<PagesSite>(
      token,
      `/repos/${repo.owner}/${repo.repo}/pages`,
      {
        method: 'POST',
        body: JSON.stringify(body),
      },
      fetchImpl,
    );

    return {
      attempted: true,
      status: 'created',
      htmlUrl: created?.html_url ?? buildDefaultPagesUrl(repo.owner, repo.repo),
      sourceBranch: created?.source?.branch ?? defaultBranch,
      sourcePath: created?.source?.path ?? sourcePath,
      buildType: created?.build_type ?? 'workflow',
    };
  }
}

async function triggerWorkflowDispatch(
  token: string,
  repo: RepoRef,
  workflowId: string,
  ref: string,
  fetchImpl: typeof fetch,
): Promise<void> {
  await githubInstallationRequest(
    token,
    `/repos/${repo.owner}/${repo.repo}/actions/workflows/${encodeURIComponent(workflowId)}/dispatches`,
    {
      method: 'POST',
      body: JSON.stringify({ ref }),
    },
    fetchImpl,
  );
}

export async function deployWithInstallation(
  config: GitHubAppConfig,
  request: DeployRequest,
  fetchImpl: typeof fetch = fetch,
): Promise<DeployResult> {
  const installationToken = await getScopedInstallationToken(
    config,
    request.installationId,
    request.repo.repo,
    fetchImpl,
  );

  const repoInfo = await getRepository(installationToken.token, request.repo, fetchImpl);
  const defaultBranch = repoInfo.default_branch ?? 'main';
  const commitMessage = request.commitMessage?.trim() || DEFAULT_COMMIT_MESSAGE;
  const workflowsToEnable = request.workflowsToEnable?.length
    ? request.workflowsToEnable
    : DEFAULT_WORKFLOWS;
  const configurePages = request.configurePages !== false;
  const pagesSourcePath = request.pagesSourcePath ?? '/';
  const autoEnableActions = request.autoEnableActions !== false;
  const triggerWorkflowId = request.triggerWorkflowId ?? 'daily.yml';
  const triggerWorkflowRef = request.triggerWorkflowRef ?? defaultBranch;

  const committedPaths = await upsertRepositoryFiles(
    installationToken.token,
    request.repo,
    defaultBranch,
    request.files,
    commitMessage,
    fetchImpl,
  );

  const writtenSecrets = await upsertRepositorySecrets(
    installationToken.token,
    request.repo,
    request.secrets,
    fetchImpl,
  );

  const actionsResult: DeployResult['actions'] = {
    attempted: autoEnableActions,
    enabled: false,
    enabledWorkflows: [],
  };

  if (autoEnableActions) {
    await setRepositoryActionsEnabled(installationToken.token, request.repo, fetchImpl);
    actionsResult.enabled = true;

    for (const workflowId of workflowsToEnable) {
      await enableWorkflow(installationToken.token, request.repo, workflowId, fetchImpl);
      actionsResult.enabledWorkflows.push(workflowId);
    }
  }

  const pagesResult = configurePages
    ? await ensurePagesSite(installationToken.token, request.repo, defaultBranch, pagesSourcePath, fetchImpl)
    : {
        attempted: false,
        status: 'skipped' as const,
        htmlUrl: null,
        sourceBranch: null,
        sourcePath: null,
        buildType: null,
      };

  await triggerWorkflowDispatch(
    installationToken.token,
    request.repo,
    triggerWorkflowId,
    triggerWorkflowRef,
    fetchImpl,
  );

  return {
    repo: {
      owner: request.repo.owner,
      repo: request.repo.repo,
      defaultBranch,
      htmlUrl: repoInfo.html_url ?? `https://github.com/${request.repo.owner}/${request.repo.repo}`,
    },
    committedPaths,
    writtenSecrets,
    actions: actionsResult,
    pages: pagesResult,
    workflowDispatch: {
      attempted: true,
      workflowId: triggerWorkflowId,
      ref: triggerWorkflowRef,
      triggered: true,
    },
  };
}
