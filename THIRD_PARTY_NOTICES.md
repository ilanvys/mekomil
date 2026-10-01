# Third-party notices

## skills-il

mekomIL reads the public [skills-il](https://github.com/skills-il) catalog. Two kinds of that
content pass through this project:

- **The catalog shards** in [`mcp/data/catalog/`](mcp/data/catalog/) quote each skill's
  `description` verbatim. This is the repository's single generated metadata copy.
- **Skill files** (`SKILL.md`, `SKILL_HE.md`, references and scripts) are fetched live and
  returned by the MCP service's `get_skill` tool. Every response carries the line
  `license: MIT, Copyright (c) 2026 Skills IL (Yootech)`.

Skill file bodies are not persisted in this repository. The running service keeps a bounded
in-memory cache of public file bodies for up to one hour. mekomIL is not affiliated with, endorsed by, or
operated by skills-il or YooTech.

Source repositories: `accounting`, `communication`, `courses`, `developer-tools`, `education`,
`food-and-dining`, `government-services`, `health-services`, `legal-tech`, `localization`,
`marketing-growth`, `security-compliance`, `tax-and-finance`, `travel`, all under
[github.com/skills-il](https://github.com/skills-il). Each ships the license below. The
`courses` repository declares it per course in `metadata.json`.

```
MIT License

Copyright (c) 2026 Skills IL (Yootech)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## MCP dependencies

The root MIT license covers this project's original code. The MCP service's dependencies
retain their own licenses, recorded in `package-lock.json`. The locked production dependency
inventory includes:

| License | Packages (including optional platform variants) |
|---|---|
| MIT | Next.js, React/React DOM, MCP SDK, Zod and other packages |
| Apache-2.0 | `mcp-handler`, `@swc/helpers`, `detect-libc`, Sharp and Sharp binary packages |
| LGPL-3.0-or-later | optional Sharp/libvips packages; some Sharp packages declare combined licenses |
| BSD-3-Clause | `source-map-js` |
| ISC | `picocolors`, `semver` |
| CC-BY-4.0 | `caniuse-lite` |
| 0BSD | `tslib` |

The source repository and skill/plugin bundles do not vendor `node_modules` or native
binaries. Installations obtain dependencies through npm. If distributing a built server,
container or dependency bundle separately, include its dependency license/notice files and
check the applicable requirements for the packages actually included, especially optional
native components. Do not treat the project's MIT license as replacing dependency licenses.
