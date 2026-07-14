#include "render/filament_backend.hpp"

#include <catch2/catch_test_macros.hpp>

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

class TemporaryGlb final {
public:
  explicit TemporaryGlb(const char *name) {
    path_ = std::filesystem::temp_directory_path() /
            (std::string{"mascotrender-semantic-robot-"} + name + ".glb");
    const auto bytes = semantic_robot_glb();
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
