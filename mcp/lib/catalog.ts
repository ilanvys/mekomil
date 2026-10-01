// All clients fetch catalog metadata here through get_catalog.
import { readFile, readdir } from "node:fs/promises";
import { join } from "node:path";
import { AppError } from "@/lib/errors";

const DIR = join(process.cwd(), "data", "catalog");

export async function categories(): Promise<string[]> {
  const files = await readdir(DIR);
  return files
    .filter((f) => f.endsWith(".md") && f !== "_index.md")
    .map((f) => f.replace(/\.md$/, ""))
    .sort();
}

export async function shard(category?: string): Promise<string> {
  if (category !== undefined && !/^[a-z0-9-]+$/.test(category)) {
    throw new AppError(
      "UNKNOWN_CATEGORY",
      `Unknown category "${category}".`,
      { knownCategories: await categories() },
    );
  }
  const name = category !== undefined ? `${category}.md` : "_index.md";
  try {
    return await readFile(join(DIR, name), "utf8");
  } catch (error) {
    const missing =
      typeof error === "object" && error !== null && "code" in error && error.code === "ENOENT";
    if (category === undefined || !missing) {
      throw new AppError(
        "CATALOG_UNAVAILABLE",
        "The catalog is unavailable.",
        { retryable: true },
      );
    }
    const known = await categories();
    throw new AppError(
      "UNKNOWN_CATEGORY",
      `Unknown category "${category}".`,
      { knownCategories: known },
    );
  }
}
