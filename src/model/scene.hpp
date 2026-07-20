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

struct Point {
  float x{};
  float y{};
};

struct SceneAnimationNode {
  std::string id;
  Point pivot;
};

struct SceneLayer {
  std::string id;
  std::filesystem::path source;
  std::vector<std::pair<std::uint32_t, std::filesystem::path>> lod_sources;
  AffineTransform transform;
  std::vector<SceneAnimationNode> animation_chain;
  float opacity{1.0F};
  float depth{};
  bool screen_space{};
  std::int32_t z{};
  std::optional<Rect> collision_bounds;
};

struct TextShell {
  float offset_x{};
  float offset_y{};
  Color color;
};

struct TextBlock {
  std::filesystem::path font;
  std::string content;
  std::vector<Rect> candidate_areas;
  std::vector<Rect> avoid_regions;
  bool auto_placement{};
  bool strict_collision{};
  float min_font_size{};
  float max_font_size{};
  std::uint32_t max_lines{};
  Color fill;
  Color outline;
  float outline_width{};
  float translate_x{};
  float translate_y{};
  float rotation_degrees{};
  float scale{1.0F};
  std::optional<TextShell> depth_shell;
  std::optional<TextShell> highlight_shell;
};

enum class AnimationLoop { once, loop, ping_pong, hold_last_frame };

enum class TextMotion { none, pop, pulse, wobble, float_motion };

enum class AnimationProperty {
  translate_x,
  translate_y,
  scale_x,
  scale_y,
  rotation_degrees,
  opacity,
  view_x,
  view_y
};

enum class AnimationEasing { linear, ease_out, ease_in_out, back_out };

struct AnimationKeyframe {
  std::uint32_t at_ms{};
  float value{};
  AnimationEasing easing{AnimationEasing::linear};
};

struct AnimationTrack {
  std::string target;
  AnimationProperty property{AnimationProperty::translate_x};
  std::vector<AnimationKeyframe> keyframes;
};

struct AnimationSpec {
  std::uint32_t duration_ms{};
  std::uint32_t fps{};
  AnimationLoop loop{AnimationLoop::once};
  bool body_bounce{};
  TextMotion text_motion{TextMotion::none};
  std::vector<AnimationTrack> tracks;
};

struct NodeFrameState {
  std::string target;
  float translate_x{};
  float translate_y{};
  float scale_x{1.0F};
  float scale_y{1.0F};
  float rotation_degrees{};
  float opacity{1.0F};
};

struct FrameState {
  float mascot_offset_y{};
  float mascot_scale{1.0F};
  float text_scale{1.0F};
  float text_opacity{1.0F};
  float text_translate_x{};
  float text_translate_y{};
  float text_rotation_degrees{};
  float view_offset_x{};
  float view_offset_y{};
  std::vector<NodeFrameState> nodes;
};

struct Scene {
  std::uint32_t width{};
  std::uint32_t height{};
  std::vector<SceneLayer> layers;
  AffineTransform camera_transform;
  float view_offset_x{};
  float view_offset_y{};
  std::vector<TextBlock> text;
  std::optional<AnimationSpec> animation;
};

[[nodiscard]] Result<Scene>
load_scene(const std::filesystem::path &pack_file,
           const std::filesystem::path &sticker_file);

} // namespace mascotrender::detail
