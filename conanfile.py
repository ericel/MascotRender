from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy

import os


class MascotRenderRecipe(ConanFile):
    name = "mascotrender"
    version = "0.5.0"
    package_type = "library"
    description = "Deterministic procedural character rendering engine"
    license = "MIT"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_cli": [True, False],
        "with_filament": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_cli": True,
        "with_filament": False,
        "thorvg/*:shared": False,
        "libwebp/*:shared": False,
    }
    exports_sources = (
        ".gitattributes",
        "CMakeLists.txt",
        "LICENSE",
        "cmake/*",
        "include/*",
        "src/*",
        "apps/*",
        "docs/*",
        "tests/*",
        "schemas/*",
        "contracts/*",
        "content/*",
        "art/human-pack-v1/*",
        "art/human-pack-wave2/*",
        "art/micro-reactions-v1/*",
        "art/calendar-pop-v1/*",
        "art/congratulations-pop-v1/*",
        "examples/*",
        "!examples/*/.DS_Store",
        "!examples/**/.DS_Store",
        "tools/*",
        "!tools/__pycache__/*",
        "!tests/__pycache__/*",
    )

    def requirements(self):
        self.requires("thorvg/0.15.16")
        self.requires("libwebp/1.6.0")
        self.requires("nlohmann_json/3.12.0")
        if self.options.with_cli:
            self.requires("cli11/2.6.2")
        if self.options.with_filament:
            self.requires("filament/1.74.0")

    def build_requirements(self):
        self.test_requires("catch2/3.15.2")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, "20")
        else:
            raise ConanInvalidConfiguration(
                "MascotRender requires compiler.cppstd=20 or newer"
            )

    def layout(self):
        cmake_layout(self)

    def generate(self):
        dependencies = CMakeDeps(self)
        dependencies.generate()

        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["MASCOTRENDER_BUILD_CLI"] = bool(self.options.with_cli)
        toolchain.variables["MASCOTRENDER_BUILD_TESTS"] = False
        toolchain.variables["MASCOTRENDER_WITH_FILAMENT"] = bool(
            self.options.with_filament
        )
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "*.txt",
            src=os.path.join(self.source_folder, "examples"),
            dst=os.path.join(self.package_folder, "licenses", "fonts"),
            keep_path=True,
        )

    def package_info(self):
        self.cpp_info.libs = ["mascotrender"]
        self.cpp_info.resdirs = ["share/mascotrender"]
        self.cpp_info.set_property("cmake_file_name", "MascotRender")
        self.cpp_info.set_property(
            "cmake_target_name", "MascotRender::MascotRender"
        )
