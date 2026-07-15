from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout

import json
import os
import shutil
import sys


class MascotRenderTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            executable = os.path.join(
                self.cpp.build.bindirs[0], "mascotrender_package_test"
            )
            resources = os.path.join(
                self.dependencies["mascotrender"].package_folder,
                "share",
                "mascotrender",
            )
            self.run(f'"{executable}" "{resources}"', env="conanrun")

            dependency = self.dependencies["mascotrender"]
            if not dependency.options.get_safe("with_cli"):
                return

            package_folder = dependency.package_folder
            generator = os.path.join(
                resources, "tools", "generate_mascot_packs.py"
            )
            renderer = os.path.join(
                resources, "tools", "render_mascot_packs.py"
            )
            reviewer = os.path.join(
                resources, "tools", "build_sticker_review.py"
            )
            cli_name = (
                "mascotrender.exe"
                if str(self.settings.os) == "Windows"
                else "mascotrender"
            )
            cli = os.path.join(package_folder, "bin", cli_name)
            pipeline_root = os.path.join(self.build_folder, "installed-pipeline")
            shutil.rmtree(pipeline_root, ignore_errors=True)
            generated = os.path.join(pipeline_root, "mascots")
            bundle = os.path.join(pipeline_root, "bundle")
            self.run(
                f'"{sys.executable}" -B "{generator}" --output "{generated}" --count 1'
            )
            self.run(
                f'"{sys.executable}" -B "{renderer}" --input "{generated}" '
                f'--output "{bundle}" --mascotrender "{cli}"'
            )
            self.run(
                f'"{sys.executable}" -B "{reviewer}" --input "{bundle}" '
                f'--expected-count 10'
            )
            self._test_installed_human_pilots(resources, cli)
            self._test_installed_canonical_humans(resources, cli)
            if dependency.options.get_safe("with_filament"):
                self._test_installed_filament_preview(dependency, resources)

    def _test_installed_human_pilots(self, resources, cli):
        validator = os.path.join(
            resources, "tools", "validate_human_pilots.py"
        )
        generator = os.path.join(
            resources, "tools", "generate_human_pilots.py"
        )
        packager = os.path.join(
            resources, "tools", "build_mascot_package.py"
        )
        human_root = os.path.join(self.build_folder, "installed-human-pilots")
        report = os.path.join(human_root, "contract-validation.json")
        generated = os.path.join(human_root, "generated")
        shutil.rmtree(human_root, ignore_errors=True)
        os.makedirs(human_root, exist_ok=True)

        self.run(
            f'"{sys.executable}" -B "{validator}" --report "{report}"'
        )
        self.run(
            f'"{sys.executable}" -B "{generator}" --output "{generated}" '
            "--count 1"
        )
        self.run(f'"{sys.executable}" -B "{packager}" --help')

        manifest_path = os.path.join(generated, "generation-manifest.json")
        with open(manifest_path, "r", encoding="utf-8") as manifest_file:
            manifest = json.load(manifest_file)
        if (
            manifest.get("pack_count") != 1
            or manifest.get("sticker_count") != 12
            or manifest.get("asset_class") != "technical-fixture"
            or manifest.get("production_use") != "forbidden"
        ):
            raise ConanException(
                "installed human pilot generator produced an unexpected manifest"
            )

        pack_id = manifest["packs"][0]["pack_id"]
        pack_root = os.path.join(generated, pack_id)
        pack = os.path.join(pack_root, "pack.json")
        stickers = os.path.join(pack_root, "stickers")
        sticker_paths = sorted(
            os.path.join(stickers, name)
            for name in os.listdir(stickers)
            if name.endswith(".json")
        )
        if len(sticker_paths) != 12:
            raise ConanException(
                "installed human pilot generator did not produce 12 stickers"
            )
        for sticker in sticker_paths:
            self.run(
                f'"{cli}" validate --pack "{pack}" --sticker "{sticker}"',
                env="conanrun",
            )

    def _test_installed_canonical_humans(self, resources, cli):
        generator = os.path.join(
            resources, "tools", "generate_canonical_human_masters.py"
        )
        glb_generator = os.path.join(
            resources, "tools", "generate_canonical_human_glbs.py"
        )
        output = os.path.join(self.build_folder, "installed-canonical-humans")
        shutil.rmtree(output, ignore_errors=True)
        self.run(f'"{sys.executable}" -B "{generator}" --output "{output}"')
        self.run(f'"{sys.executable}" -B "{glb_generator}" --input "{output}"')
        with open(
            os.path.join(output, "generation-manifest.json"),
            "r",
            encoding="utf-8",
        ) as manifest_file:
            manifest = json.load(manifest_file)
        if (
            manifest.get("master_count") != 5
            or manifest.get("status") != "owner-vector-parity-approved"
            or manifest.get("production_use") != "forbidden"
        ):
            raise ConanException(
                "installed canonical human generator produced an unexpected manifest"
            )
        validated = 0
        for master_id in ("H01", "H04", "H07", "H12", "H13"):
            master = os.path.join(output, master_id)
            pack = os.path.join(master, "pack.json")
            stickers = os.path.join(master, "stickers")
            sticker_paths = sorted(
                os.path.join(directory, name)
                for directory, _, names in os.walk(stickers)
                for name in names
                if name.endswith(".json")
            )
            expected = 40 if master_id == "H01" else 41
            if len(sticker_paths) != expected:
                raise ConanException(
                    f"installed canonical master {master_id} has an incomplete review specification set"
                )
            for sticker in sticker_paths:
                self.run(
                    f'"{cli}" validate --pack "{pack}" --sticker "{sticker}"',
                    env="conanrun",
                )
                validated += 1
            self.run(
                f'"{cli}" validate --pack "{os.path.join(master, "pack-flat.json")}" '
                f'--sticker "{os.path.join(stickers, "production", "happy.json")}"',
                env="conanrun",
            )
        if validated != 204:
            raise ConanException("installed canonical human pipeline did not validate 204 render specifications")
        with open(os.path.join(output, "glb-manifest.json"), "r", encoding="utf-8") as glb_file:
            glb_manifest = json.load(glb_file)
        if glb_manifest.get("master_count") != 5:
            raise ConanException("installed canonical human GLB generation is incomplete")

    def _test_installed_filament_preview(self, dependency, resources):
        executable_name = (
            "mascotrender-glb-preview.exe"
            if str(self.settings.os) == "Windows"
            else "mascotrender-glb-preview"
        )
        preview = os.path.join(dependency.package_folder, "bin", executable_name)
        if str(self.settings.os) == "Windows":
            # Hosted Windows runners have no Vulkan ICD. Starting the installed
            # executable still verifies the packaged binary and static links;
            # pixel rendering is covered on macOS and Linux.
            self.run(f'"{preview}" --help', env="conanrun")
            return
        model = os.path.join(resources, "examples", "robot-004", "robot-004.glb")
        output = os.path.join(self.build_folder, "installed-filament-preview.webp")
        self.run(
            f'"{preview}" --input "{model}" --output "{output}" '
            "--width 64 --height 64 --span 3.85 --center-y 0.15",
            env="conanrun",
        )
        if not os.path.isfile(output):
            raise ConanException("installed Filament preview did not create output")
        with open(output, "rb") as rendered:
            payload = rendered.read()
        if (
            len(payload) < 100
            or payload[:4] != b"RIFF"
            or payload[8:12] != b"WEBP"
        ):
            raise ConanException(
                "installed Filament preview did not produce a valid WebP container"
            )
