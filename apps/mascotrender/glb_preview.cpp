#include "render/filament_backend.hpp"

#include <webp/encode.h>

#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

[[nodiscard]] const char *next_value(int &index, int argc, char **argv) {
  if (index + 1 >= argc) {
    throw std::invalid_argument{std::string{"missing value for "} +
                                argv[index]};
  }
  return argv[++index];
}

void print_help() {
  std::cout << "Usage: mascotrender-glb-preview --input model.glb --output "
               "frame.webp\n"
               "       [--width 256] [--height 256] [--span 3.6] "
               "[--center-y 0.0]\n"
               "       [--animation clip] [--time seconds]\n";
}

} // namespace

int main(int argc, char **argv) {
  std::filesystem::path input;
  std::filesystem::path output;
  mascotrender::detail::FilamentRenderOptions options;
  try {
    for (int index = 1; index < argc; ++index) {
      const std::string argument{argv[index]};
      if (argument == "--input") {
        input = next_value(index, argc, argv);
      } else if (argument == "--output") {
        output = next_value(index, argc, argv);
      } else if (argument == "--width") {
        options.width = static_cast<std::uint32_t>(
            std::stoul(next_value(index, argc, argv)));
      } else if (argument == "--height") {
        options.height = static_cast<std::uint32_t>(
            std::stoul(next_value(index, argc, argv)));
      } else if (argument == "--span") {
        options.vertical_span = std::stof(next_value(index, argc, argv));
      } else if (argument == "--center-y") {
        options.vertical_center = std::stof(next_value(index, argc, argv));
      } else if (argument == "--animation") {
        options.animation_name = next_value(index, argc, argv);
      } else if (argument == "--time") {
        options.animation_time_seconds =
            std::stof(next_value(index, argc, argv));
      } else if (argument == "--help" || argument == "-h") {
        print_help();
        return 0;
      } else {
        throw std::invalid_argument{"unknown argument: " + argument};
      }
    }
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    print_help();
    return 2;
  }
  if (input.empty() || output.empty()) {
    print_help();
    return 2;
  }

  auto rendered = mascotrender::detail::render_filament_glb(input, options);
  if (!rendered) {
    std::cerr << "render failed: " << rendered.error().message << '\n';
    return 1;
  }

  const auto &frame = rendered.value();
  const auto stride = static_cast<std::size_t>(frame.width) * 4U;

  std::uint8_t *encoded = nullptr;
  const auto encoded_size = WebPEncodeLosslessRGBA(
      frame.rgba.data(), static_cast<int>(frame.width),
      static_cast<int>(frame.height), static_cast<int>(stride), &encoded);
  if (encoded_size == 0U || encoded == nullptr) {
    std::cerr << "WebP encoding failed\n";
    return 1;
  }

  std::error_code directory_error;
  if (!output.parent_path().empty()) {
    std::filesystem::create_directories(output.parent_path(), directory_error);
  }
  std::ofstream stream{output, std::ios::binary};
  stream.write(reinterpret_cast<const char *>(encoded),
               static_cast<std::streamsize>(encoded_size));
  WebPFree(encoded);
  if (!stream) {
    std::cerr << "could not write: " << output << '\n';
    return 1;
  }
  std::cout << "wrote " << frame.width << 'x' << frame.height
            << " lossless WebP to " << output << '\n';
  return 0;
}
