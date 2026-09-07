import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { mkdtemp, readdir, readFile, realpath, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { test } from "node:test";
import { promisify } from "node:util";
import { assertSameFiles, repoRoot, skillsRoot } from "./distribution-helpers.mjs";

const exec = promisify(execFile);
const cli = path.join(repoRoot, "node_modules/skills/bin/cli.mjs");

for (const mode of ["symlink", "copy"]) {
  test(`Skills installs canonical content for Claude Code, Codex, and Gemini CLI (${mode})`, { timeout: 60000 }, async (t) => {
    const project = await mkdtemp(path.join(tmpdir(), "boltz-skills-install-"));
    t.after(() => rm(project, { recursive: true, force: true }));
    await exec(process.execPath, [cli, "add", repoRoot, "--skill", "*", "--agent", "claude-code", "codex", "gemini-cli", "--yes",
      ...(mode === "copy" ? ["--copy"] : [])], {
      cwd: project,
      env: { ...process.env, DISABLE_TELEMETRY: "1", DO_NOT_TRACK: "1", CI: "1" },
      timeout: 45000,
      maxBuffer: 1024 * 1024
    });

    const names = (await readdir(skillsRoot)).sort();
    const projectRoot = await realpath(project);
    // Codex and Gemini CLI both consume the universal .agents/skills directory.
    for (const directory of [".claude/skills", ".agents/skills"]) {
      const installed = path.join(project, directory);
      assert.deepEqual((await readdir(installed)).sort(), names);
      for (const name of names) {
        const destination = await realpath(path.join(installed, name));
        assert.ok(destination.startsWith(projectRoot + path.sep), `Install points outside the test project: ${destination}`);
      }
      // Agent links may be symlinks; the contents of each installed skill must be real files.
      for (const name of names) {
        await assertSameFiles(path.join(skillsRoot, name), path.join(installed, name));
      }
    }
    const lock = JSON.parse(await readFile(path.join(project, "skills-lock.json"), "utf8"));
    assert.deepEqual(Object.keys(lock.skills).sort(), names);
    for (const entry of Object.values(lock.skills)) {
      assert.equal(entry.sourceType, "local");
    }
  });
}
