from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout

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
                f'"{sys.executable}" "{generator}" --output "{generated}" --count 1'
            )
            self.run(
                f'"{sys.executable}" "{renderer}" --input "{generated}" '
                f'--output "{bundle}" --mascotrender "{cli}"'
            )
            self.run(
                f'"{sys.executable}" "{reviewer}" --input "{bundle}" '
                f'--expected-count 10'
            )
            if dependency.options.get_safe("with_filament"):
                self._test_installed_filament_preview(dependency, resources)

    def _test_installed_filament_preview(self, dependency, resources):
        executable_name = (
            "mascotrender-glb-preview.exe"
            if str(self.settings.os) == "Windows"
            else "mascotrender-glb-preview"
        )
        preview = os.path.join(dependency.package_folder, "bin", executable_name)
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
