#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <string_view>

#include <mascotrender/mascotrender.hpp>

int main(int argc, char** argv) {
    if (std::string_view{mascotrender::version_string()} != "0.1.0") {
        return 1;
    }

    mascotrender::Engine engine;
    if (argc != 2) {
        return 2;
    }
    const std::filesystem::path resources{argv[1]};
    const auto example = resources / "examples" / "cat";
    const mascotrender::RenderRequest request{
        example / "pack.json", example / "stickers" / "text-sample.json", {}};
    auto result = engine.render(request);
    if (!result) {
        return 3;
    }
    const auto& image = result.value();
    if (image.width != 512 || image.height != 512 || image.bytes.size() < 12) {
        return 4;
    }
    const auto character = [&image](std::size_t index) {
        return static_cast<char>(std::to_integer<std::uint8_t>(image.bytes[index]));
    };
    if (character(0) != 'R' || character(1) != 'I' || character(2) != 'F' ||
        character(3) != 'F' || character(8) != 'W' || character(9) != 'E' ||
        character(10) != 'B' || character(11) != 'P') {
        return 5;
    }

    std::ofstream output{"mascotrender-package-test.webp", std::ios::binary};
    output.write(reinterpret_cast<const char*>(image.bytes.data()),
                 static_cast<std::streamsize>(image.bytes.size()));
    return output ? 0 : 6;
}
