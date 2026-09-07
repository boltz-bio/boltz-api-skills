import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { assertSameSkills, repoRoot } from "./distribution-helpers.mjs";

const temp = await mkdtemp(path.join(tmpdir(), "boltz-packages-"));
try {
  for (const [surface, manifestFile, artifactName, extension] of [
    ["claude-code-cli", ".claude-plugin/plugin.json", "claude-code-cli", "zip"],
    ["codex-cli", ".codex-plugin/plugin.json", "boltz-api-cli", "zip"],
    ["gemini-cli", "gemini-extension.json", "boltz-gemini-cli", "zip"],
    ["mcpb", "manifest.json", "boltz-mcpb", "mcpb"]
  ]) {
    const manifest = JSON.parse(await readFile(path.join(repoRoot, "surfaces", surface, manifestFile), "utf8"));
    const archive = path.join(repoRoot, "dist", `${artifactName}-${manifest.version}.${extension}`);
    const extracted = path.join(temp, surface);
    execFileSync("unzip", ["-q", archive, "-d", extracted]);
    await assertSameSkills(path.join(extracted, surface === "mcpb" ? "guidance/skills" : "skills"));
    const packagedManifest = JSON.parse(await readFile(path.join(extracted, manifestFile), "utf8"));
    assert.deepEqual(packagedManifest, manifest);
    if (surface === "codex-cli") {
      assert.ok((await readFile(path.join(extracted, "assets/app-icon.png"))).length > 0);
    }
    if (surface === "gemini-cli") {
      assert.ok((await readFile(path.join(extracted, "GEMINI.md"))).length > 0);
    }
    if (surface === "mcpb") {
      // Import from the unpacked bundle, where no repository source fallback exists.
      const { guidanceResources } = await import(pathToFileURL(path.join(extracted, "server/guidance.js")).href);
      for (const resource of guidanceResources) {
        const result = await resource.read(new URL(resource.uri));
        assert.ok(result.contents[0].text.length > 0, `Empty packaged guidance: ${resource.uri}`);
      }
    }
    console.log(`Verified ${path.basename(archive)}`);
  }
} finally {
  await rm(temp, { recursive: true, force: true });
}
