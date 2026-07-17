#include <algorithm>
#include <filesystem>
#include <optional>
#include <string>
#include <string_view>

#include <catch2/catch_test_macros.hpp>

#include "model/scene.hpp"
#include "render/caption_layout.hpp"
#include "render/text_layout.hpp"

namespace {

[[nodiscard]] std::optional<mascotrender::detail::TextMetrics>
monospace_measure(std::string_view text, float font_size) {
  return mascotrender::detail::TextMetrics{
      0.0F, 0.0F, static_cast<float>(text.size()), font_size};
}

} // namespace

TEST_CASE("balanced wrapping improves a valid greedy split") {
  const auto fitted = mascotrender::detail::fit_text_balanced(
      "AAAA BBBB CC", 9.0F, 30.0F, 10.0F, 10.0F, 2U, 0.0F, monospace_measure);

  REQUIRE(fitted);
  REQUIRE(fitted->lines.size() == 2U);
  REQUIRE(fitted->lines[0] == "AAAA");
  REQUIRE(fitted->lines[1] == "BBBB CC");
}

TEST_CASE("balanced wrapping keeps one line when it fits") {
  const auto fitted = mascotrender::detail::fit_text_balanced(
      "ONE LINE", 20.0F, 20.0F, 10.0F, 10.0F, 3U, 0.0F, monospace_measure);

  REQUIRE(fitted);
  REQUIRE(fitted->lines.size() == 1U);
  REQUIRE(fitted->lines.front() == "ONE LINE");
}

TEST_CASE("outline inset participates in fitting") {
  const auto no_outline = mascotrender::detail::fit_text_balanced(
      "AAAA BBBB", 9.0F, 30.0F, 10.0F, 10.0F, 2U, 0.0F, monospace_measure);
  const auto outlined = mascotrender::detail::fit_text_balanced(
      "AAAA BBBB", 9.0F, 30.0F, 10.0F, 10.0F, 2U, 1.0F, monospace_measure);

  REQUIRE(no_outline);
  REQUIRE(no_outline->lines.size() == 1U);
  REQUIRE(outlined);
  REQUIRE(outlined->lines.size() == 2U);
}

TEST_CASE("one collision-aware caption layout resolves for flat and layered scenes") {
  const std::filesystem::path source_root{MASCOTRENDER_TEST_SOURCE_DIR};
  const auto pack = source_root / "examples" / "robot-2_5d";
  const auto sticker = pack / "stickers" / "caption-proof.json";
  const auto layered =
      mascotrender::detail::load_scene(pack / "pack.json", sticker);
  const auto flat =
      mascotrender::detail::load_scene(pack / "pack-flat.json", sticker);
  REQUIRE(layered);
  REQUIRE(flat);
  REQUIRE(layered.value().text.size() == 1U);
  REQUIRE(flat.value().text.size() == 1U);

  const auto layered_caption = mascotrender::detail::resolve_caption(
      layered.value().text.front(), 1.0F, 1.0F, monospace_measure);
  const auto flat_caption = mascotrender::detail::resolve_caption(
      flat.value().text.front(), 1.0F, 1.0F, monospace_measure);
  REQUIRE(layered_caption);
  REQUIRE(flat_caption);
  REQUIRE(layered_caption->candidate_index == 1U);
  REQUIRE(flat_caption->candidate_index == layered_caption->candidate_index);
  REQUIRE(flat_caption->area.x == layered_caption->area.x);
  REQUIRE(flat_caption->area.y == layered_caption->area.y);
  REQUIRE(flat_caption->fitted.lines == layered_caption->fitted.lines);
  REQUIRE(flat_caption->positions.front().x ==
          layered_caption->positions.front().x);
  REQUIRE(flat_caption->positions.front().y ==
          layered_caption->positions.front().y);
}

TEST_CASE("caption avoidance unions collision bounds across animation frames") {
  const std::filesystem::path source_root{MASCOTRENDER_TEST_SOURCE_DIR};
  const auto pack = source_root / "examples" / "robot-2_5d";
  const auto scene = mascotrender::detail::load_scene(
      pack / "pack.json",
      pack / "stickers" / "animated-caption-collision-proof.json");
  REQUIRE(scene);
  REQUIRE(scene.value().animation);
  REQUIRE(scene.value().text.size() == 1U);
  const auto &regions = scene.value().text.front().avoid_regions;
  REQUIRE(regions.size() >= 3U);
  REQUIRE(std::any_of(regions.begin(), regions.end(), [](const auto &region) {
    return region.height >= 300.0F;
  }));
}

TEST_CASE("strict caption collision rejects an overlapping preferred slot") {
  using mascotrender::detail::Color;
  using mascotrender::detail::Rect;
  using mascotrender::detail::TextBlock;
  const TextBlock block{
      {},
      "CAPTION",
      {Rect{0, 0, 100, 40}, Rect{0, 60, 100, 40}},
      {Rect{0, 0, 100, 40}},
      true,
      true,
      10,
      20,
      2,
      Color{255, 255, 255},
      Color{0, 0, 0},
      1};
  const auto resolved = mascotrender::detail::resolve_caption(
      block, 1.0F, 1.0F, monospace_measure);
  REQUIRE(resolved);
  REQUIRE(resolved->candidate_index == 1U);
}
