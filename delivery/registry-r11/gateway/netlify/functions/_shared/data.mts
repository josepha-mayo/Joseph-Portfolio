import { readFile, stat } from "node:fs/promises";
import { resolve } from "node:path";
import type { RegistryData } from "./registry.mts";

export async function loadData(directory = resolve("data")): Promise<RegistryData> {
  async function bounded(name: string): Promise<Uint8Array> {
    const path = resolve(directory, name);
    if ((await stat(path)).size > 262144) throw new Error("Registry data exceeds bound");
    const result = await readFile(path);
    if (result.length > 262144) throw new Error("Registry data exceeds bound");
    return result;
  }
  const [manifest, imageConfig, routing] = await Promise.all([
    bounded("final-manifest.json"), bounded("final-config.json"), bounded("routing-map.json"),
  ]);
  return { manifest, imageConfig, routing: JSON.parse(new TextDecoder().decode(routing)) };
}
