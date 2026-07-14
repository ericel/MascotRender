#include "model/scene.hpp"
#include "render/caption_compositor.hpp"
#include "render/filament_backend.hpp"
#include "render/thorvg_backend.hpp"

#include <catch2/catch_test_macros.hpp>

#include <algorithm>
#include <array>
#include <bit>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <limits>
#include <string>
#include <vector>

namespace {

const std::filesystem::path source_root{MASCOTRENDER_TEST_SOURCE_DIR};
const auto robot_glb = source_root / "examples/robot-004/robot-004.glb";

void append_u32(std::vector<std::uint8_t> &bytes, std::uint32_t value) {
  bytes.push_back(static_cast<std::uint8_t>(value));
  bytes.push_back(static_cast<std::uint8_t>(value >> 8U));
  bytes.push_back(static_cast<std::uint8_t>(value >> 16U));
  bytes.push_back(static_cast<std::uint8_t>(value >> 24U));
}

void append_float(std::vector<std::uint8_t> &bytes, float value) {
  append_u32(bytes, std::bit_cast<std::uint32_t>(value));
}

[[nodiscard]] std::uint64_t
frame_hash(const std::vector<std::uint8_t> &bytes) noexcept {
  std::uint64_t hash = 14695981039346656037ULL;
  for (const auto byte : bytes) {
    hash ^= byte;
    hash *= 1099511628211ULL;
  }
  return hash;
}

[[nodiscard]] std::size_t
lit_pixel_count(const std::vector<std::uint8_t> &rgba) noexcept {
  std::size_t count = 0U;
  for (std::size_t index = 0; index < rgba.size(); index += 4U) {
    count += static_cast<unsigned>(rgba[index]) +
                             static_cast<unsigned>(rgba[index + 1U]) +
                             static_cast<unsigned>(rgba[index + 2U]) >
                         30U &&
                     rgba[index + 3U] > 0U
                 ? 1U
                 : 0U;
  }
  return count;
}

[[nodiscard]] std::size_t
color_pixel_count(const mascotrender::detail::FilamentFrame &frame,
                  const std::array<std::uint8_t, 3> target,
                  std::uint32_t first_row = 0U, std::uint32_t last_row = 0U,
                  std::uint8_t tolerance = 3U) noexcept {
  if (last_row == 0U) {
    last_row = frame.height;
  }
  std::size_t count = 0U;
  for (auto y = first_row; y < last_row; ++y) {
    for (std::uint32_t x = 0U; x < frame.width; ++x) {
      const auto index = (static_cast<std::size_t>(y) * frame.width + x) * 4U;
      bool matches = frame.rgba[index + 3U] > 200U;
      for (std::size_t channel = 0U; channel < target.size(); ++channel) {
        const auto actual = static_cast<int>(frame.rgba[index + channel]);
        const auto expected = static_cast<int>(target[channel]);
        matches = matches && std::abs(actual - expected) <= tolerance;
      }
      count += matches ? 1U : 0U;
    }
  }
  return count;
}

struct PixelBounds final {
  std::size_t count{0U};
  std::uint32_t left{std::numeric_limits<std::uint32_t>::max()};
  std::uint32_t top{std::numeric_limits<std::uint32_t>::max()};
  std::uint32_t right{0U};
  std::uint32_t bottom{0U};

  [[nodiscard]] std::uint32_t width() const noexcept { return right - left; }
};

[[nodiscard]] PixelBounds
translucent_pixel_bounds(const mascotrender::detail::FilamentFrame &frame,
                         std::uint32_t first_row) noexcept {
  PixelBounds bounds;
  for (auto y = first_row; y < frame.height; ++y) {
    for (std::uint32_t x = 0U; x < frame.width; ++x) {
      const auto alpha =
          frame.rgba[(static_cast<std::size_t>(y) * frame.width + x) * 4U + 3U];
      if (alpha < 90U || alpha > 130U) {
        continue;
      }
      ++bounds.count;
      bounds.left = std::min(bounds.left, x);
      bounds.top = std::min(bounds.top, y);
      bounds.right = std::max(bounds.right, x + 1U);
      bounds.bottom = std::max(bounds.bottom, y + 1U);
    }
  }
  return bounds;
}

[[nodiscard]] std::vector<std::uint8_t> semantic_robot_glb() {
  std::string json =
      R"({"asset":{"version":"2.0","generator":"MascotRender"},"scene":0,"scenes":[{"nodes":[0]}],"nodes":[{"name":"RobotRoot","children":[1,2,3]},{"name":"Head"},{"name":"Antenna"},{"name":"caption_anchor","translation":[0,1.5,0]}]})";
  while (json.size() % 4U != 0U) {
    json.push_back(' ');
  }

  std::vector<std::uint8_t> bytes;
  bytes.reserve(20U + json.size());
  bytes.insert(bytes.end(), {'g', 'l', 'T', 'F'});
  append_u32(bytes, 2U);
  append_u32(bytes, static_cast<std::uint32_t>(20U + json.size()));
  append_u32(bytes, static_cast<std::uint32_t>(json.size()));
  bytes.insert(bytes.end(), {'J', 'S', 'O', 'N'});
  bytes.insert(bytes.end(), json.begin(), json.end());
  return bytes;
}

[[nodiscard]] std::vector<std::uint8_t> renderable_robot_glb() {
  std::string json =
      R"({"asset":{"version":"2.0","generator":"MascotRender"},"scene":0,"scenes":[{"nodes":[0]}],"nodes":[{"name":"RobotRoot","children":[1]},{"name":"Head","mesh":0}],"meshes":[{"primitives":[{"attributes":{"POSITION":0,"NORMAL":1},"indices":2,"material":0}]}],"materials":[{"pbrMetallicRoughness":{"baseColorFactor":[0.08,0.75,0.32,1.0],"metallicFactor":0.0,"roughnessFactor":1.0},"doubleSided":true}],"buffers":[{"byteLength":80}],"bufferViews":[{"buffer":0,"byteOffset":0,"byteLength":36,"target":34962},{"buffer":0,"byteOffset":36,"byteLength":36,"target":34962},{"buffer":0,"byteOffset":72,"byteLength":6,"target":34963}],"accessors":[{"bufferView":0,"componentType":5126,"count":3,"type":"VEC3","min":[-0.75,-0.7,0.0],"max":[0.75,0.8,0.0]},{"bufferView":1,"componentType":5126,"count":3,"type":"VEC3"},{"bufferView":2,"componentType":5123,"count":3,"type":"SCALAR"}]})";
  while (json.size() % 4U != 0U) {
    json.push_back(' ');
  }

  std::vector<std::uint8_t> binary;
  binary.reserve(80U);
  for (const float component :
       {-0.75F, -0.7F, 0.0F, 0.75F, -0.7F, 0.0F, 0.0F, 0.8F, 0.0F}) {
    append_float(binary, component);
  }
  for (int vertex = 0; vertex < 3; ++vertex) {
    append_float(binary, 0.0F);
    append_float(binary, 0.0F);
    append_float(binary, 1.0F);
  }
  binary.insert(binary.end(), {0U, 0U, 1U, 0U, 2U, 0U, 0U, 0U});

  std::vector<std::uint8_t> bytes;
  bytes.reserve(28U + json.size() + binary.size());
  bytes.insert(bytes.end(), {'g', 'l', 'T', 'F'});
  append_u32(bytes, 2U);
  append_u32(bytes,
             static_cast<std::uint32_t>(28U + json.size() + binary.size()));
  append_u32(bytes, static_cast<std::uint32_t>(json.size()));
  bytes.insert(bytes.end(), {'J', 'S', 'O', 'N'});
  bytes.insert(bytes.end(), json.begin(), json.end());
  append_u32(bytes, static_cast<std::uint32_t>(binary.size()));
  bytes.insert(bytes.end(), {'B', 'I', 'N', 0U});
  bytes.insert(bytes.end(), binary.begin(), binary.end());
  return bytes;
}

class TemporaryGlb final {
public:
  explicit TemporaryGlb(const char *name, std::vector<std::uint8_t> bytes =
                                              semantic_robot_glb()) {
    path_ = std::filesystem::temp_directory_path() /
            (std::string{"mascotrender-semantic-robot-"} + name + ".glb");
    std::ofstream output{path_, std::ios::binary};
    REQUIRE(output);
    output.write(reinterpret_cast<const char *>(bytes.data()),
                 static_cast<std::streamsize>(bytes.size()));
    REQUIRE(output);
  }

  ~TemporaryGlb() {
    std::error_code ignored;
    std::filesystem::remove(path_, ignored);
  }

  [[nodiscard]] const std::filesystem::path &path() const noexcept {
    return path_;
  }

private:
  std::filesystem::path path_;
};

} // namespace

TEST_CASE("Filament loads GLB semantic anchors behind backend-neutral data") {
  const TemporaryGlb fixture{"anchors"};
  const std::vector<std::string> required{"RobotRoot", "Head", "Antenna",
                                          "caption_anchor"};
  const auto inspected =
      mascotrender::detail::inspect_filament_glb(fixture.path(), required);

  REQUIRE(inspected);
  REQUIRE(inspected.value().entity_count == 4U);
  REQUIRE(inspected.value().renderable_count == 0U);
  REQUIRE(inspected.value().camera_count == 0U);
  REQUIRE(inspected.value().light_count == 0U);
  REQUIRE(inspected.value().animation_count == 0U);
  REQUIRE(inspected.value().morph_target_count == 0U);
  REQUIRE(inspected.value().semantic_anchors == required);
}

TEST_CASE("Filament GLB loader rejects a missing semantic anchor") {
  const TemporaryGlb fixture{"missing"};
  const auto inspected = mascotrender::detail::inspect_filament_glb(
      fixture.path(), {"RobotRoot", "missing_anchor"});

  REQUIRE_FALSE(inspected);
  REQUIRE(inspected.error().code == mascotrender::ErrorCode::invalid_document);
  REQUIRE(inspected.error().message.find("missing_anchor") !=
          std::string::npos);
}

TEST_CASE("Filament renders a GLB through a square orthographic camera") {
  const TemporaryGlb fixture{"render", renderable_robot_glb()};
  const auto rendered = mascotrender::detail::render_filament_glb(
      fixture.path(), {.width = 96U, .height = 96U, .vertical_span = 2.5F});

  REQUIRE(rendered);
  REQUIRE(rendered.value().width == 96U);
  REQUIRE(rendered.value().height == 96U);
  REQUIRE(rendered.value().rgba.size() == 96U * 96U * 4U);

  std::size_t opaque_pixels = 0U;
  for (std::size_t index = 0; index < rendered.value().rgba.size();
       index += 4U) {
    const auto alpha = rendered.value().rgba[index + 3U];
    opaque_pixels += alpha > 0U ? 1U : 0U;
  }
  REQUIRE(opaque_pixels > 500U);
  REQUIRE(opaque_pixels < 5000U);
}

TEST_CASE("Filament render bounds reject unsafe output sizes") {
  const auto rendered = mascotrender::detail::render_filament_glb(
      "unused.glb", {.width = 0U, .height = 96U, .vertical_span = 2.5F});

  REQUIRE_FALSE(rendered);
  REQUIRE(rendered.error().code == mascotrender::ErrorCode::invalid_argument);

  const auto invalid_center = mascotrender::detail::render_filament_glb(
      "unused.glb",
      {.width = 96U,
       .height = 96U,
       .vertical_span = 2.5F,
       .vertical_center = std::numeric_limits<float>::infinity()});
  REQUIRE_FALSE(invalid_center);
  REQUIRE(invalid_center.error().code ==
          mascotrender::ErrorCode::invalid_argument);
}

TEST_CASE("Filament uses the shared screen-space caption compositor") {
  constexpr std::uint32_t size = 256U;
  auto rendered = mascotrender::detail::render_filament_glb(
      robot_glb, {.width = size,
                  .height = size,
                  .vertical_span = 4.4F,
                  .vertical_center = 0.35F});
  REQUIRE(rendered);
  const auto base_hash = frame_hash(rendered.value().rgba);

  const auto pack = source_root / "examples" / "robot-2_5d";
  auto scene = mascotrender::detail::load_scene(
      pack / "pack.json", pack / "stickers" / "caption-proof.json");
  REQUIRE(scene);
  mascotrender::detail::ThorvgBackend caption_renderer;
  auto caption =
      caption_renderer.render_caption_overlay(scene.value(), size, size);
  REQUIRE(caption);
  auto sparkle =
      caption_renderer.render_layer_overlay(scene.value(), "spark", size, size);
  REQUIRE(sparkle);
  auto with_effect = mascotrender::detail::composite_overlay(
      std::move(rendered.value()), sparkle.value());
  REQUIRE(with_effect);
  REQUIRE(frame_hash(with_effect.value().rgba) != base_hash);

  auto composited = mascotrender::detail::composite_overlay(
      std::move(with_effect.value()), caption.value());
  REQUIRE(composited);
  REQUIRE(frame_hash(composited.value().rgba) != base_hash);

  std::size_t white_caption_pixels = 0U;
  for (std::uint32_t y = 219U; y < size; ++y) {
    for (std::uint32_t x = 0U; x < size; ++x) {
      const auto index = (static_cast<std::size_t>(y) * size + x) * 4U;
      white_caption_pixels +=
          composited.value().rgba[index] > 245U &&
                  composited.value().rgba[index + 1U] > 245U &&
                  composited.value().rgba[index + 2U] > 245U &&
                  composited.value().rgba[index + 3U] > 245U
              ? 1U
              : 0U;
    }
  }
  REQUIRE(white_caption_pixels > 100U);
}

TEST_CASE("authored robot GLB exposes four clips and six facial morphs") {
  const std::vector<std::string> anchors{
      "RobotRoot", "Body", "Head", "Face", "Antenna", "caption_anchor"};
  const auto inspected =
      mascotrender::detail::inspect_filament_glb(robot_glb, anchors);

  REQUIRE(inspected);
  REQUIRE(inspected.value().entity_count == 19U);
  REQUIRE(inspected.value().renderable_count == 13U);
  REQUIRE(inspected.value().animation_count == 4U);
  REQUIRE(inspected.value().animation_names ==
          std::vector<std::string>{"idle", "hello", "hop", "celebrate"});
  REQUIRE(inspected.value().animation_durations_seconds.size() == 4U);
  for (const auto duration : inspected.value().animation_durations_seconds) {
    REQUIRE(duration >= 0.9F);
    REQUIRE(duration <= 1.0F);
  }
  REQUIRE(inspected.value().morph_target_count == 6U);
  REQUIRE(inspected.value().morph_target_names ==
          std::vector<std::string>{"blink", "smile", "wow", "squint", "sad",
                                   "cheek"});
  REQUIRE(inspected.value().semantic_anchors == anchors);
}

TEST_CASE("authored robot clips produce distinct orthographic frames") {
  const mascotrender::detail::FilamentRenderOptions rest_options{
      .width = 128U, .height = 128U, .vertical_span = 3.6F};
  const auto rest =
      mascotrender::detail::render_filament_glb(robot_glb, rest_options);
  REQUIRE(rest);
  REQUIRE(lit_pixel_count(rest.value().rgba) > 2000U);
  REQUIRE(color_pixel_count(rest.value(), {255U, 209U, 102U}) > 1000U);
  REQUIRE(color_pixel_count(rest.value(), {233U, 154U, 32U}) > 500U);
  REQUIRE(color_pixel_count(rest.value(), {99U, 217U, 207U}) > 10U);
  REQUIRE(color_pixel_count(rest.value(), {89U, 212U, 204U}) > 20U);
  REQUIRE(color_pixel_count(rest.value(), {38U, 52U, 81U}) > 100U);
  const auto tip_on_top = color_pixel_count(rest.value(), {89U, 212U, 204U}, 0U,
                                            rest.value().height / 4U);
  const auto tip_on_bottom = color_pixel_count(rest.value(), {89U, 212U, 204U},
                                               rest.value().height * 3U / 4U);
  REQUIRE(tip_on_top > tip_on_bottom);
  const auto rest_hash = frame_hash(rest.value().rgba);

  for (const auto &[clip, time] :
       std::vector<std::pair<std::string, float>>{{"idle", 0.5F},
                                                  {"hello", 0.3F},
                                                  {"hop", 0.3F},
                                                  {"celebrate", 0.5F}}) {
    auto options = rest_options;
    options.animation_name = clip;
    options.animation_time_seconds = time;
    const auto animated =
        mascotrender::detail::render_filament_glb(robot_glb, options);
    CAPTURE(clip, time);
    REQUIRE(animated);
    REQUIRE(frame_hash(animated.value().rgba) != rest_hash);
  }
}

TEST_CASE("authored robot hop contracts its independent contact shadow") {
  const mascotrender::detail::FilamentRenderOptions rest_options{
      .width = 128U, .height = 128U, .vertical_span = 3.6F};
  const auto rest =
      mascotrender::detail::render_filament_glb(robot_glb, rest_options);
  auto hop_options = rest_options;
  hop_options.animation_name = "hop";
  hop_options.animation_time_seconds = 0.3F;
  const auto hop =
      mascotrender::detail::render_filament_glb(robot_glb, hop_options);

  REQUIRE(rest);
  REQUIRE(hop);
  const auto lower_quarter = rest.value().height * 3U / 4U;
  const auto rest_shadow =
      translucent_pixel_bounds(rest.value(), lower_quarter);
  const auto hop_shadow = translucent_pixel_bounds(hop.value(), lower_quarter);
  REQUIRE(rest_shadow.count > 0U);
  REQUIRE(hop_shadow.count > 0U);
  REQUIRE(hop_shadow.width() * 100U <= rest_shadow.width() * 70U);
  REQUIRE(hop_shadow.count * 100U <= rest_shadow.count * 70U);
  const auto rest_center_twice = rest_shadow.left + rest_shadow.right;
  const auto hop_center_twice = hop_shadow.left + hop_shadow.right;
  REQUIRE(std::abs(static_cast<int>(rest_center_twice) -
                   static_cast<int>(hop_center_twice)) <= 2);
}

TEST_CASE("authored robot rejects an unknown animation clip") {
  const auto rendered = mascotrender::detail::render_filament_glb(
      robot_glb, {.width = 64U,
                  .height = 64U,
                  .vertical_span = 3.6F,
                  .animation_name = "missing",
                  .animation_time_seconds = 0.0F});

  REQUIRE_FALSE(rendered);
  REQUIRE(rendered.error().code == mascotrender::ErrorCode::invalid_argument);
  REQUIRE(rendered.error().message.find("missing") != std::string::npos);
}
