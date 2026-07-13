# Third-party notices

MascotRender 0.1.0 uses the following pinned dependencies. The complete license
files are distributed in their respective Conan packages; this inventory is
derived from the locked Conan dependency graph.

| Component | Version | Use | Declared license |
|---|---:|---|---|
| ThorVG | 0.15.16 | Private software vector/text renderer | MIT |
| libwebp | 1.6.0 | Private WebP encoder/decoder | BSD-3-Clause |
| libjpeg-turbo | 3.1.4.1 | Transitive image dependency | IJG, BSD-3-Clause, Zlib |
| libpng | 1.6.47 | Transitive image dependency | libpng-2.0 |
| zlib | 1.3.1 | Transitive compression dependency | Zlib |
| nlohmann JSON | 3.12.0 | Private JSON parser | MIT |
| CLI11 | 2.6.2 | Optional CLI dependency | BSD-3-Clause |
| Catch2 | 3.15.2 | Test-only dependency | BSL-1.0 |

The example and generated packs include Changa One Regular from the Google
Fonts repository at revision `ec0464b978de222073645d6d3366f3fdf03376d8`.
The font is licensed under SIL Open Font License 1.1. Its complete `OFL.txt`,
upstream metadata, provenance, and static TTF are stored with the example pack
and copied into each generated pack.

Build-only tools such as CMake, Meson, Ninja, and pkgconf are not linked into or
redistributed by the MascotRender library package. Conan records and distributes
their licenses with their own packages.

MascotRender itself is distributed under the MIT License. The complete project
license is shipped at the package root and under the Conan `licenses`
directory. Third-party components and content remain under their listed terms.
