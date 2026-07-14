#include "render/filament_backend.hpp"

#include <catch2/catch_test_macros.hpp>

#include <bit>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

namespace {

void append_u32(std::vector<std::uint8_t> &bytes, std::uint32_t value) {
  bytes.push_back(static_cast<std::uint8_t>(value));
  bytes.push_back(static_cast<std::uint8_t>(value >> 8U));
  bytes.push_back(static_cast<std::uint8_t>(value >> 16U));
  bytes.push_back(static_cast<std::uint8_t>(value >> 24U));
}

void append_float(std::vector<std::uint8_t> &bytes, float value) {
  append_u32(bytes, std::bit_cast<std::uint32_t>(value));
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

TEST_CASE("Filament renders a lit GLB through a square orthographic camera") {
  const TemporaryGlb fixture{"render", renderable_robot_glb()};
  const auto rendered = mascotrender::detail::render_filament_glb(
      fixture.path(), {.width = 96U, .height = 96U, .vertical_span = 2.5F});

  REQUIRE(rendered);
  REQUIRE(rendered.value().width == 96U);
  REQUIRE(rendered.value().height == 96U);
  REQUIRE(rendered.value().rgba.size() == 96U * 96U * 4U);

  std::size_t opaque_pixels = 0U;
  std::size_t green_pixels = 0U;
  for (std::size_t index = 0; index < rendered.value().rgba.size();
       index += 4U) {
    const auto red = rendered.value().rgba[index];
    const auto green = rendered.value().rgba[index + 1U];
    const auto blue = rendered.value().rgba[index + 2U];
    const auto alpha = rendered.value().rgba[index + 3U];
    opaque_pixels += alpha > 0U ? 1U : 0U;
    green_pixels += green > red && green > blue && alpha > 0U ? 1U : 0U;
  }
  REQUIRE(opaque_pixels > 500U);
  REQUIRE(opaque_pixels < 5000U);
  REQUIRE(green_pixels > 500U);
}

TEST_CASE("Filament render bounds reject unsafe output sizes") {
  const auto rendered = mascotrender::detail::render_filament_glb(
      "unused.glb", {.width = 0U, .height = 96U, .vertical_span = 2.5F});

  REQUIRE_FALSE(rendered);
  REQUIRE(rendered.error().code == mascotrender::ErrorCode::invalid_argument);
}
