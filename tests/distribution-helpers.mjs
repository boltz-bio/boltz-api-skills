import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const repoRoot = fileURLToPath(new URL("../", import.meta.url));
export const skillsRoot = path.join(repoRoot, "skills");

export async function filesIn(directory) {
  const files = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (entry.name === "__pycache__" || entry.name === ".DS_Store" || /\.py[cod]$/.test(entry.name)) continue;
    assert.equal(entry.isSymbolicLink(), false, `Skill content must be self-contained: ${directory}/${entry.name}`);
    if (entry.isDirectory()) {
      for (const nested of await filesIn(path.join(directory, entry.name))) {
        files.push(path.join(entry.name, nested));
      }
    } else {
      files.push(entry.name);
    }
  }
  return files.sort();
}

export async function assertSameFiles(expectedRoot, actualRoot) {
  const expected = await filesIn(expectedRoot);
  assert.deepEqual(await filesIn(actualRoot), expected, `Skill files differ: ${actualRoot}`);
  for (const file of expected) {
    assert.deepEqual(
      await readFile(path.join(actualRoot, file)),
      await readFile(path.join(expectedRoot, file)),
      `Skill content differs: ${actualRoot}/${file}`
    );
  }
}

export async function assertSameSkills(actualRoot) {
  await assertSameFiles(skillsRoot, actualRoot);
}
