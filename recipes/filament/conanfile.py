from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get

import os


class FilamentRecipe(ConanFile):
    name = "filament"
    version = "1.74.0"
    package_type = "static-library"
    description = "Real-time physically based rendering engine"
    license = "Apache-2.0"
    homepage = "https://github.com/google/filament"
    settings = "os", "arch", "compiler", "build_type"

    _core_libraries = (
        "filament",
        "backend",
        "bluegl",
        "bluevk",
        "filabridge",
        "filaflat",
        "utils",
        "geometry",
        "smol-v",
        "ibl",
        "abseil",
        "zstd",
    )
    _gltfio_libraries = (
        "gltfio",
        "filamat",
        "gltfio_core",
        "dracodec",
        "meshoptimizer",
        "ktxreader",
        "uberzlib",
        "stb",
        "basis_transcoder",
        "shaders",
    )

    def validate(self):
        platform = (str(self.settings.os), str(self.settings.arch))
        supported = {
            ("Macos", "armv8"),
            ("Linux", "x86_64"),
            ("Windows", "x86_64"),
        }
        if platform not in supported:
            raise ConanInvalidConfiguration(
                "Filament 1.74.0 binary wrapper supports macOS armv8, "
                "Linux x86_64, and Windows x86_64"
            )
        compiler = str(self.settings.compiler)
        if self.settings.os == "Macos" and (
            compiler != "apple-clang"
            or str(self.settings.compiler.get_safe("libcxx")) != "libc++"
        ):
            raise ConanInvalidConfiguration(
                "The macOS Filament binary requires AppleClang and libc++"
            )
        if self.settings.os == "Linux" and (
            compiler != "clang"
            or str(self.settings.compiler.get_safe("libcxx")) != "libc++"
        ):
            raise ConanInvalidConfiguration(
                "The official Linux Filament binary requires Clang and libc++"
            )
        if self.settings.os == "Windows" and compiler != "msvc":
            raise ConanInvalidConfiguration(
                "The Windows Filament binary requires MSVC"
            )

    def build(self):
        key = f"{self.settings.os}-{self.settings.arch}"
        source = self.conan_data["sources"][str(self.version)][key]
        get(
            self,
            source["url"],
            sha256=source["sha256"],
            strip_root=source["strip_root"],
            destination=self.build_folder,
        )

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "*",
            src=os.path.join(self.build_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "*",
            src=self._library_source_folder(),
            dst=os.path.join(self.package_folder, "lib"),
        )
        self._validate_package_contents()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "filament")
        self.cpp_info.set_property("cmake_target_name", "filament::all")

        core = self.cpp_info.components["filament"]
        core.set_property("cmake_target_name", "filament::filament")
        core.libs = list(self._core_libraries)

        gltfio = self.cpp_info.components["gltfio"]
        gltfio.set_property("cmake_target_name", "filament::gltfio")
        gltfio.libs = list(self._gltfio_libraries)
        gltfio.requires = ["filament"]

        if self.settings.os == "Macos":
            core.frameworks = ["Cocoa", "Metal", "CoreVideo", "QuartzCore"]
        elif self.settings.os == "Linux":
            core.system_libs = ["pthread", "dl"]
        elif self.settings.os == "Windows":
            core.system_libs = ["gdi32", "user32", "opengl32"]

    def _library_source_folder(self):
        base = os.path.join(self.build_folder, "lib")
        if self.settings.os == "Macos":
            return os.path.join(base, "arm64")
        if self.settings.os == "Linux":
            return os.path.join(base, "x86_64")

        runtime = str(self.settings.compiler.runtime)
        runtime_type = str(self.settings.compiler.runtime_type)
        suffix = "d" if runtime_type == "Debug" else ""
        variant = ("md" if runtime == "dynamic" else "mt") + suffix
        return os.path.join(base, "x86_64", variant)

    def _validate_package_contents(self):
        required_headers = (
            os.path.join("filament", "Engine.h"),
            os.path.join("gltfio", "AssetLoader.h"),
            os.path.join("gltfio", "MaterialProvider.h"),
        )
        missing = [
            os.path.join("include", header)
            for header in required_headers
            if not os.path.isfile(
                os.path.join(self.package_folder, "include", header)
            )
        ]

        for library in self._core_libraries + self._gltfio_libraries:
            if self.settings.os == "Windows":
                filename = f"{library}.lib"
            else:
                filename = f"lib{library}.a"
            if not os.path.isfile(
                os.path.join(self.package_folder, "lib", filename)
            ):
                missing.append(os.path.join("lib", filename))

        license_path = os.path.join(self.package_folder, "licenses", "LICENSE")
        if not os.path.isfile(license_path):
            missing.append(os.path.join("licenses", "LICENSE"))
        if missing:
            raise ConanException(
                "Filament binary archive is missing required package files: "
                + ", ".join(missing)
            )
