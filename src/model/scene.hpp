#pragma once

#include <cstdint>
#include <filesystem>
#include <mascotrender/result.hpp>
#include <optional>
#include <string>
#include <vector>

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

struct AffineTransform {
  float m11{1.0F};
  float m12{};
  float m21{};
  float m22{1.0F};
  float translate_x{};
  float translate_y{};
};

struct SceneLayer {
  std::string id;
  std::filesystem::path source;
  AffineTransform transform;
  float opacity{1.0F};
  float depth{};
  std::int32_t z{};
};

struct TextBlock {
  std::filesystem::path font;
  std::string content;
  std::vector<Rect> candidate_areas;
  std::vector<Rect> avoid_regions;
  bool auto_placement{};
  float min_font_size{};
  float max_font_size{};
  std::uint32_t max_lines{};
  Color fill;
  Color outline;
  float outline_width{};
};

enum class AnimationLoop { once, loop, ping_pong, hold_last_frame };

struct AnimationSpec {
  std::uint32_t duration_ms{};
  std::uint32_t fps{};
  AnimationLoop loop{AnimationLoop::once};
  bool body_bounce{};
  bool text_pop{};
};

struct FrameState {
  float mascot_offset_y{};
  float mascot_scale{1.0F};
  float text_scale{1.0F};
  float text_opacity{1.0F};
};

struct Scene {
  std::uint32_t width{};
  std::uint32_t height{};
  std::vector<SceneLayer> layers;
  float view_offset_x{};
  float view_offset_y{};
  std::vector<TextBlock> text;
  std::optional<AnimationSpec> animation;
};

[[nodiscard]] Result<Scene>
load_scene(const std::filesystem::path &pack_file,
           const std::filesystem::path &sticker_file);

} // namespace mascotrender::detail
