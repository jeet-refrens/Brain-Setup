declare module "libnpmpack" {
  function pack(spec?: string, opts?: Record<string, unknown>): Promise<Buffer>;
  export default pack;
}
