#pragma once

#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>

#include <mascotrender/result.hpp>

namespace mascotrender::detail {

struct Color {
  std::uint8_t red{};
  std::uint8_t green{};
  std::uint8_t blue{};
};

struct Rect {
  float x{};
  float y{};
  float width{};
  float height{};
};

struct TextBlock {
  std::filesystem::path font;
  std::string content;
  Rect safe_area;
  float min_font_size{};
  float max_font_size{};
  std::uint32_t max_lines{};
  Color fill;
  Color outline;
  float outline_width{};
};

struct Scene {
  std::uint32_t width{};
  std::uint32_t height{};
  std::vector<std::filesystem::path> layers;
  std::vector<TextBlock> text;
};

[[nodiscard]] Result<Scene>
load_scene(const std::filesystem::path &pack_file,
           const std::filesystem::path &sticker_file);

} // namespace mascotrender::detail
