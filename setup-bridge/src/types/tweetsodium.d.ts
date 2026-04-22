declare module 'tweetsodium' {
  export type TweetSodiumApi = {
    seal(message: Uint8Array, publicKey: Uint8Array): Uint8Array;
    sealOpen(ciphertext: Uint8Array, publicKey: Uint8Array, secretKey: Uint8Array): Uint8Array | null;
    overheadLength: number;
  };

  const tweetsodium: TweetSodiumApi;
  export default tweetsodium;
}
