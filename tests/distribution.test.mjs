import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { access, mkdtemp, readdir, readFile, realpath, rm, stat, utimes, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { test } from "node:test";
import { promisify } from "node:util";
import { parse } from "yaml";
import { assertSameSkills, filesIn, repoRoot, skillsRoot } from "./distribution-helpers.mjs";

test("public skill metadata follows the Agent Skills specification", async () => {
  for (const directory of await readdir(skillsRoot)) {
    const markdown = await readFile(path.join(skillsRoot, directory, "SKILL.md"), "utf8");
    const frontmatter = markdown.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/);
    assert.ok(frontmatter, `${directory}: missing YAML frontmatter`);
    const metadata = parse(frontmatter[1]);
    assert.equal(metadata.name, directory, `${directory}: name must match its directory`);
    assert.match(metadata.name, /^[a-z0-9]+(?:-[a-z0-9]+)*$/);
    assert.ok(metadata.name.length <= 64, `${directory}: name exceeds 64 characters`);
    assert.equal(typeof metadata.description, "string");
    assert.ok(metadata.description.trim().length > 0 && metadata.description.length <= 1024,
      `${directory}: description must contain 1–1024 characters`);
    assert.notEqual(metadata.metadata?.internal, true, `${directory}: public skills must remain discoverable`);
    assert.notEqual(metadata.metadata?.internal, "true", `${directory}: public skills must remain discoverable`);
    assert.ok(markdown.split(/\r?\n/).length < 500,
      `${directory}: move detailed content to references to stay below 500 lines`);
  }
});

test("canonical skills contain their referenced documents and agent metadata", async () => {
  const names = await readdir(skillsRoot);
  for (const name of names) {
    const root = path.join(skillsRoot, name);
    await access(path.join(root, "SKILL.md"));
    await access(path.join(root, "agents/openai.yaml"));
    for (const file of await filesIn(root)) {
      if (!file.endsWith(".md")) continue;
      const markdown = (await readFile(path.join(root, file), "utf8")).replace(/```[\s\S]*?```/g, "");
      for (const match of markdown.matchAll(/\[[^\]]+\]\(([^\s)]+)\)/g)) {
        const target = match[1].split("#")[0];
        if (!target || /^[a-z][a-z\d+.-]*:/i.test(target)) continue;
        const resolved = path.resolve(root, path.dirname(file), target);
        const relative = path.relative(root, resolved);
        assert.ok(relative !== ".." && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative),
          `${name}/${file} references a file outside the skill: ${target}`);
        await access(resolved);
      }
    }
  }
});

test("CLI compatibility wrappers share the canonical skill tree", async () => {
  for (const surface of ["claude-code-cli", "codex-cli", "gemini-cli"]) {
    assert.equal(await realpath(path.join(repoRoot, "surfaces", surface, "skills")), await realpath(skillsRoot));
  }
});

test("generated marketplace and MCPB packages contain the complete canonical skills", async () => {
  for (const directory of ["plugins/boltz/skills", "plugins/boltz-api-cli/skills", "plugins/boltz-mcpb/guidance/skills"]) {
    await assertSameSkills(path.join(repoRoot, directory));
  }
});

test("official Claude and Codex marketplace identities and metadata are preserved", async () => {
  const readJson = async (file) => JSON.parse(await readFile(path.join(repoRoot, file), "utf8"));
  const marketplace = await readJson(".claude-plugin/marketplace.json");
  const claudeEntry = marketplace.plugins.find((plugin) => plugin.name === "boltz");
  assert.ok(claudeEntry, "The official Claude marketplace entry must remain available");
  const claude = await readJson(path.join(claudeEntry.source, ".claude-plugin/plugin.json"));
  assert.equal(claude.name, "boltz");
  assert.deepEqual(claude, await readJson("surfaces/claude-code-cli/.claude-plugin/plugin.json"));
  const codex = await readJson("plugins/boltz-api-cli/.codex-plugin/plugin.json");
  assert.equal(codex.name, "boltz-api-cli");
  assert.equal(codex.skills, "./skills");
  assert.deepEqual(codex, await readJson("surfaces/codex-cli/.codex-plugin/plugin.json"));
  for (const field of ["composerIcon", "logo"]) {
    await access(path.join(repoRoot, "plugins/boltz-api-cli", codex.interface[field]));
  }
});

test("generation repairs stale files even when size and timestamps match", async (t) => {
  const output = await mkdtemp(path.join(tmpdir(), "boltz-generation-"));
  t.after(() => rm(output, { recursive: true, force: true }));
  const generate = () => promisify(execFile)("bash", [path.join(repoRoot, "scripts/generate-surfaces.sh"), output]);
  await generate();
  const source = path.join(repoRoot, "surfaces/codex-cli/.codex-plugin/plugin.json");
  const target = path.join(output, "boltz-api-cli/.codex-plugin/plugin.json");
  const original = await readFile(source);
  const corrupted = Buffer.from(original);
  corrupted[corrupted.indexOf("boltz-api-cli")] = "x".charCodeAt(0);
  await writeFile(target, corrupted);
  const sourceStat = await stat(source);
  await utimes(target, sourceStat.atime, sourceStat.mtime);
  await generate();
  assert.deepEqual(await readFile(target), original);
});
