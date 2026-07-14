#include <webp/decode.h>
#include <webp/demux.h>

#include <catch2/catch_test_macros.hpp>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <mascotrender/mascotrender.hpp>
#include <vector>

#include "model/scene.hpp"

namespace {

const std::filesystem::path source_root{MASCOTRENDER_TEST_SOURCE_DIR};

[[nodiscard]] mascotrender::RenderRequest
example_request(const std::filesystem::path &sticker = "sample.json") {
  const auto pack = source_root / "examples" / "cat";
  return mascotrender::RenderRequest{
      pack / "pack.json", pack / "stickers" / sticker, {}};
}

[[nodiscard]] mascotrender::RenderRequest
robot_2_5d_request(const std::filesystem::path &pack_file = "pack.json",
                   const std::filesystem::path &sticker_file = "flat.json") {
  const auto pack = source_root / "examples" / "robot-2_5d";
  return mascotrender::RenderRequest{
      pack / pack_file, pack / "stickers" / sticker_file, {}};
}

struct Pixel {
  std::uint8_t blue{};
  std::uint8_t green{};
  std::uint8_t red{};
  std::uint8_t alpha{};
};

[[nodiscard]] std::vector<std::uint8_t>
decode(const mascotrender::EncodedImage &image) {
  std::vector<std::uint8_t> pixels(static_cast<std::size_t>(image.width) *
                                   image.height * 4U);
  const auto *encoded =
      reinterpret_cast<const std::uint8_t *>(image.bytes.data());
  REQUIRE(WebPDecodeBGRAInto(encoded, image.bytes.size(), pixels.data(),
                             pixels.size(),
                             static_cast<int>(image.width * 4U)) != nullptr);
  return pixels;
}

[[nodiscard]] Pixel pixel_at(const std::vector<std::uint8_t> &pixels,
                             std::uint32_t width, std::uint32_t x,
                             std::uint32_t y) {
  const auto offset = (static_cast<std::size_t>(y) * width + x) * 4U;
  return Pixel{pixels.at(offset), pixels.at(offset + 1U),
               pixels.at(offset + 2U), pixels.at(offset + 3U)};
}

[[nodiscard]] std::vector<std::uint8_t>
read_bytes(const std::filesystem::path &path) {
  std::ifstream input{path, std::ios::binary};
  REQUIRE(input);
  return {std::istreambuf_iterator<char>{input},
          std::istreambuf_iterator<char>{}};
}

} // namespace

TEST_CASE("versioned JSON pack and sticker render SVG layers") {
  mascotrender::Engine engine;
  const auto request = example_request();

  auto first = engine.render(request);
  REQUIRE(first);
  auto second = engine.render(request);
  REQUIRE(second);
  REQUIRE(first.value().bytes == second.value().bytes);

  const auto &image = first.value();
  WebPBitstreamFeatures features{};
  const auto *encoded =
      reinterpret_cast<const std::uint8_t *>(image.bytes.data());
  REQUIRE(WebPGetFeatures(encoded, image.bytes.size(), &features) ==
          VP8_STATUS_OK);
  REQUIRE(features.width == 512);
  REQUIRE(features.height == 512);
  REQUIRE(features.has_alpha == 1);
}

TEST_CASE("parented 2.5D nodes preserve the flat t0 render") {
  mascotrender::Engine engine;
  auto layered = engine.render(robot_2_5d_request());
  REQUIRE(layered);
  auto flat = engine.render(robot_2_5d_request("pack-flat.json"));
  REQUIRE(flat);
  REQUIRE(layered.value().bytes == flat.value().bytes);

  auto layered_thumbnail_request = robot_2_5d_request();
  layered_thumbnail_request.options.width = 256;
  layered_thumbnail_request.options.height = 256;
  auto layered_thumbnail = engine.render(layered_thumbnail_request);
  REQUIRE(layered_thumbnail);
  auto flat_thumbnail_request = robot_2_5d_request("pack-flat.json");
  flat_thumbnail_request.options.width = 256;
  flat_thumbnail_request.options.height = 256;
  auto flat_thumbnail = engine.render(flat_thumbnail_request);
  REQUIRE(flat_thumbnail);
  REQUIRE(layered_thumbnail.value().bytes == flat_thumbnail.value().bytes);

  const auto pack = source_root / "examples" / "robot-2_5d";
  auto scene = mascotrender::detail::load_scene(
      pack / "pack.json", pack / "stickers" / "flat.json");
  REQUIRE(scene);
  REQUIRE(scene.value().layers.size() == 7U);
  REQUIRE(scene.value().layers.front().id == "shadow");
  REQUIRE(scene.value().layers.back().id == "spark");
  REQUIRE(scene.value().view_offset_x == 0.0F);
  REQUIRE(scene.value().view_offset_y == 0.0F);
}

TEST_CASE(
    "parent transforms depth and opacity resolve through the scene graph") {
  const auto pack = source_root / "examples" / "robot-2_5d";
  auto scene = mascotrender::detail::load_scene(
      pack / "pack-transform.json", pack / "stickers" / "flat.json");
  REQUIRE(scene);
  REQUIRE(scene.value().layers.size() == 2U);
  const auto &body = scene.value().layers.at(0);
  const auto &head = scene.value().layers.at(1);
  REQUIRE(body.id == "body");
  REQUIRE(body.transform.translate_x == 10.0F);
  REQUIRE(body.transform.translate_y == 5.0F);
  REQUIRE(std::abs(body.depth - 0.2F) < 0.0001F);
  REQUIRE(std::abs(body.opacity - 0.8F) < 0.0001F);
  REQUIRE(head.id == "head");
  REQUIRE(head.transform.translate_x == 13.0F);
  REQUIRE(head.transform.translate_y == 7.0F);
  REQUIRE(std::abs(head.depth - 0.5F) < 0.0001F);
  REQUIRE(std::abs(head.opacity - 0.4F) < 0.0001F);
}

TEST_CASE("layer depth produces deterministic parallax") {
  mascotrender::Engine engine;
  auto first =
      engine.render(robot_2_5d_request("pack.json", "parallax-right.json"));
  REQUIRE(first);
  auto second =
      engine.render(robot_2_5d_request("pack.json", "parallax-right.json"));
  REQUIRE(second);
  auto flat = engine.render(robot_2_5d_request());
  REQUIRE(flat);
  REQUIRE(first.value().bytes == second.value().bytes);
  REQUIRE(first.value().bytes != flat.value().bytes);

  const auto parallax_pixels = decode(first.value());
  const auto flat_pixels = decode(flat.value());
  REQUIRE(pixel_at(flat_pixels, 512, 92, 262).alpha == 255);
  REQUIRE(pixel_at(parallax_pixels, 512, 92, 262).alpha == 0);
  REQUIRE(pixel_at(parallax_pixels, 512, 60, 272).alpha == 255);
}

TEST_CASE("layered 2.5D timeline encodes motion and preserves its t0 poster") {
  mascotrender::Engine engine;
  auto request = robot_2_5d_request("pack.json", "animated-hop.json");
  request.options.lossless = true;

  auto first = engine.render(request);
  REQUIRE(first);
  auto second = engine.render(request);
  REQUIRE(second);
  REQUIRE(first.value().bytes == second.value().bytes);

  const auto *encoded =
      reinterpret_cast<const std::uint8_t *>(first.value().bytes.data());
  const WebPData data{encoded, first.value().bytes.size()};
  auto *decoder = WebPAnimDecoderNew(&data, nullptr);
  REQUIRE(decoder != nullptr);
  WebPAnimInfo info{};
  REQUIRE(WebPAnimDecoderGetInfo(decoder, &info) != 0);
  REQUIRE(info.canvas_width == 512U);
  REQUIRE(info.canvas_height == 512U);
  REQUIRE(info.frame_count >= 3U);
  REQUIRE(info.loop_count == 0U);

  std::vector<std::uint8_t> first_frame;
  std::vector<std::uint8_t> changed_frame;
  std::vector<std::uint8_t> last_frame;
  std::uint8_t *frame = nullptr;
  int timestamp = 0;
  std::uint32_t frame_index = 0U;
  while (WebPAnimDecoderHasMoreFrames(decoder) != 0) {
    REQUIRE(WebPAnimDecoderGetNext(decoder, &frame, &timestamp) != 0);
    if (frame_index == 0U) {
      first_frame.assign(frame, frame + 512U * 512U * 4U);
    } else if (frame_index == info.frame_count / 2U) {
      changed_frame.assign(frame, frame + 512U * 512U * 4U);
    }
    last_frame.assign(frame, frame + 512U * 512U * 4U);
    ++frame_index;
  }
  REQUIRE(timestamp == 1200);
  REQUIRE_FALSE(changed_frame.empty());
  REQUIRE(first_frame != changed_frame);

  const auto rest_shadow_edge = pixel_at(first_frame, 512, 140, 420);
  const auto apex_shadow_edge = pixel_at(changed_frame, 512, 140, 420);
  const auto rest_shadow_center = pixel_at(first_frame, 512, 256, 420);
  const auto apex_shadow_center = pixel_at(changed_frame, 512, 264, 414);
  REQUIRE(rest_shadow_edge.alpha > 0U);
  REQUIRE(apex_shadow_edge.alpha == 0U);
  REQUIRE(apex_shadow_center.alpha < rest_shadow_center.alpha / 2U);

  const auto side_panel_pixels = [](const std::vector<std::uint8_t> &pixels) {
    std::size_t count = 0U;
    for (std::size_t offset = 0; offset < pixels.size(); offset += 4U) {
      if (pixels[offset] == 223U && pixels[offset + 1U] == 142U &&
          pixels[offset + 2U] == 36U && pixels[offset + 3U] == 255U) {
        ++count;
      }
    }
    return count;
  };
  REQUIRE(side_panel_pixels(first_frame) > 500U);
  REQUIRE(side_panel_pixels(changed_frame) > 500U);
  REQUIRE(side_panel_pixels(last_frame) > 500U);

  bool top_margin_is_clear = true;
  for (std::uint32_t y = 0U; y < 12U; ++y) {
    for (std::uint32_t x = 0U; x < 512U; ++x) {
      top_margin_is_clear =
          top_margin_is_clear && pixel_at(changed_frame, 512, x, y).alpha == 0U;
    }
  }
  REQUIRE(top_margin_is_clear);
  WebPAnimDecoderDelete(decoder);

  request.options.animation_first_frame_only = true;
  auto poster = engine.render(request);
  REQUIRE(poster);
  auto flat_request = robot_2_5d_request();
  flat_request.options.lossless = true;
  auto flat = engine.render(flat_request);
  REQUIRE(flat);
  REQUIRE(poster.value().bytes == flat.value().bytes);
}

TEST_CASE("layer parent cycles report their pack location") {
  mascotrender::Engine engine;
  auto request = example_request();
  request.pack_file =
      source_root / "tests" / "fixtures" / "layer-cycle-pack.json";
  request.sticker_file =
      source_root / "tests" / "fixtures" / "layer-cycle-sticker.json";

  auto result = engine.render(request);
  REQUIRE_FALSE(result);
  REQUIRE(result.error().code == mascotrender::ErrorCode::invalid_document);
  REQUIRE(result.error().source == request.pack_file.string());
  REQUIRE(result.error().location == "$.layers[0].parent");
}

TEST_CASE("pack render supports deterministic 256 pixel thumbnails") {
  mascotrender::Engine engine;
  auto request = example_request();
  request.options.width = 256;
  request.options.height = 256;

  auto thumbnail = engine.render(request);
  REQUIRE(thumbnail);
  REQUIRE(thumbnail.value().width == 256);
  REQUIRE(thumbnail.value().height == 256);

  WebPBitstreamFeatures features{};
  const auto *encoded =
      reinterpret_cast<const std::uint8_t *>(thumbnail.value().bytes.data());
  REQUIRE(WebPGetFeatures(encoded, thumbnail.value().bytes.size(), &features) ==
          VP8_STATUS_OK);
  REQUIRE(features.width == 256);
  REQUIRE(features.height == 256);
  REQUIRE(features.has_alpha == 1);
}

TEST_CASE("pack-declared TTF renders deterministic fitted sticker text") {
  mascotrender::Engine engine;

  auto first = engine.render(example_request("text-sample.json"));
  REQUIRE(first);
  auto second = engine.render(example_request("text-sample.json"));
  REQUIRE(second);
  REQUIRE(first.value().bytes == second.value().bytes);

  auto without_text = engine.render(example_request("sample.json"));
  REQUIRE(without_text);
  REQUIRE(first.value().bytes != without_text.value().bytes);

  const auto text_pixels = decode(first.value());
  const auto plain_pixels = decode(without_text.value());
  REQUIRE(pixel_at(text_pixels, 512, 84, 430).red > 240);
  REQUIRE(pixel_at(text_pixels, 512, 84, 430).alpha == 255);
  REQUIRE(pixel_at(plain_pixels, 512, 84, 430).alpha == 0);

  bool found_fill = false;
  bool found_outline = false;
  for (std::uint32_t y = 420; y < 486; ++y) {
    for (std::uint32_t x = 72; x < 440; ++x) {
      const auto text_pixel = pixel_at(text_pixels, 512, x, y);
      const auto plain_pixel = pixel_at(plain_pixels, 512, x, y);
      if (plain_pixel.alpha != 0 || text_pixel.alpha == 0) {
        continue;
      }
      found_fill =
          found_fill || (text_pixel.red > 240 && text_pixel.green > 240 &&
                         text_pixel.blue > 240);
      found_outline =
          found_outline || (text_pixel.red < 80 && text_pixel.green < 80 &&
                            text_pixel.blue < 100);
    }
  }
  REQUIRE(found_fill);
  REQUIRE(found_outline);

  auto thumbnail_request = example_request("text-sample.json");
  thumbnail_request.options.width = 256;
  thumbnail_request.options.height = 256;
  auto thumbnail = engine.render(thumbnail_request);
  REQUIRE(thumbnail);
  REQUIRE(thumbnail.value().width == 256);
  REQUIRE(thumbnail.value().height == 256);
}

TEST_CASE("named text slots place captions in different canvas regions") {
  mascotrender::Engine engine;

  auto top = engine.render(example_request("text-top.json"));
  REQUIRE(top);
  auto automatic = engine.render(example_request("text-auto.json"));
  REQUIRE(automatic);
  auto collision_aware = engine.render(example_request("text-auto-avoid.json"));
  REQUIRE(collision_aware);
  auto bottom = engine.render(example_request("text-bottom.json"));
  REQUIRE(bottom);
  REQUIRE(automatic.value().bytes == bottom.value().bytes);
  REQUIRE(collision_aware.value().bytes == top.value().bytes);
  REQUIRE(top.value().bytes != bottom.value().bytes);

  const auto top_pixels = decode(top.value());
  const auto bottom_pixels = decode(bottom.value());
  bool top_has_new_pixels = false;
  for (std::uint32_t y = 12; y < 108; ++y) {
    for (std::uint32_t x = 40; x < 472; ++x) {
      const auto top_pixel = pixel_at(top_pixels, 512, x, y);
      const auto bottom_pixel = pixel_at(bottom_pixels, 512, x, y);
      top_has_new_pixels = top_has_new_pixels ||
                           (top_pixel.alpha != 0 && bottom_pixel.alpha == 0);
    }
  }
  REQUIRE(top_has_new_pixels);
}

TEST_CASE("timeline overlays encode a deterministic animated WebP") {
  mascotrender::Engine engine;
  auto request = example_request("animated-bounce.json");

  auto first = engine.render(request);
  REQUIRE(first);
  auto second = engine.render(request);
  REQUIRE(second);
  REQUIRE(first.value().bytes == second.value().bytes);

  const auto *encoded =
      reinterpret_cast<const std::uint8_t *>(first.value().bytes.data());
  WebPBitstreamFeatures features{};
  REQUIRE(WebPGetFeatures(encoded, first.value().bytes.size(), &features) ==
          VP8_STATUS_OK);
  REQUIRE(features.has_animation == 1);

  const WebPData data{encoded, first.value().bytes.size()};
  auto *decoder = WebPAnimDecoderNew(&data, nullptr);
  REQUIRE(decoder != nullptr);
  WebPAnimInfo info{};
  REQUIRE(WebPAnimDecoderGetInfo(decoder, &info) != 0);
  REQUIRE(info.canvas_width == 512U);
  REQUIRE(info.canvas_height == 512U);
  REQUIRE(info.frame_count >= 2U);
  REQUIRE(info.loop_count == 0U);

  std::vector<std::uint8_t> first_frame;
  std::vector<std::uint8_t> second_frame;
  std::uint8_t *frame = nullptr;
  int timestamp = 0;
  std::uint32_t frame_index = 0U;
  while (WebPAnimDecoderHasMoreFrames(decoder) != 0) {
    REQUIRE(WebPAnimDecoderGetNext(decoder, &frame, &timestamp) != 0);
    if (frame_index == 0U) {
      first_frame.assign(frame, frame + 512U * 512U * 4U);
    } else if (frame_index == 1U) {
      second_frame.assign(frame, frame + 512U * 512U * 4U);
    }
    ++frame_index;
  }
  REQUIRE(frame_index == info.frame_count);
  REQUIRE(timestamp == 800);
  REQUIRE(first_frame != second_frame);
  WebPAnimDecoderDelete(decoder);

  request.options.animation_first_frame_only = true;
  auto poster = engine.render(request);
  REQUIRE(poster);
  WebPBitstreamFeatures poster_features{};
  const auto *poster_encoded =
      reinterpret_cast<const std::uint8_t *>(poster.value().bytes.data());
  REQUIRE(WebPGetFeatures(poster_encoded, poster.value().bytes.size(),
                          &poster_features) == VP8_STATUS_OK);
  REQUIRE(poster_features.has_animation == 0);

  request.options.animation_first_frame_only = false;
  request.options.width = 4096U;
  request.options.height = 4096U;
  auto oversized = engine.render(request);
  REQUIRE_FALSE(oversized);
  REQUIRE(oversized.error().code == mascotrender::ErrorCode::invalid_argument);
  REQUIRE(oversized.error().message.find("256 MiB") != std::string::npos);
}

TEST_CASE("reviewed text mascot remains within the decoded-pixel golden") {
  mascotrender::Engine engine;
  auto request = example_request("text-sample.json");
  request.options.lossless = true;
  auto rendered = engine.render(request);
  REQUIRE(rendered);

  const auto golden_bytes =
      read_bytes(source_root / "tests" / "golden" / "cat-text-sample.webp");
  int golden_width = 0;
  int golden_height = 0;
  REQUIRE(WebPGetInfo(golden_bytes.data(), golden_bytes.size(), &golden_width,
                      &golden_height) != 0);
  REQUIRE(golden_width == static_cast<int>(rendered.value().width));
  REQUIRE(golden_height == static_cast<int>(rendered.value().height));

  std::vector<std::uint8_t> golden_pixels(
      static_cast<std::size_t>(golden_width) * golden_height * 4U);
  REQUIRE(WebPDecodeBGRAInto(golden_bytes.data(), golden_bytes.size(),
                             golden_pixels.data(), golden_pixels.size(),
                             golden_width * 4) != nullptr);
  const auto actual_pixels = decode(rendered.value());
  REQUIRE(actual_pixels.size() == golden_pixels.size());

  std::uint64_t absolute_error = 0;
  std::size_t changed_pixels = 0;
  for (std::size_t pixel = 0; pixel < actual_pixels.size(); pixel += 4U) {
    bool changed = false;
    for (std::size_t channel = 0; channel < 4U; ++channel) {
      const auto actual = actual_pixels[pixel + channel];
      const auto golden = golden_pixels[pixel + channel];
      const auto difference =
          actual > golden ? actual - golden : golden - actual;
      absolute_error += difference;
      changed = changed || difference > 8U;
    }
    changed_pixels += changed ? 1U : 0U;
  }

  const auto mean_channel_error = static_cast<double>(absolute_error) /
                                  static_cast<double>(actual_pixels.size());
  const auto changed_ratio = static_cast<double>(changed_pixels) /
                             static_cast<double>(actual_pixels.size() / 4U);
  INFO("mean channel error: " << mean_channel_error);
  INFO("changed pixel ratio: " << changed_ratio);
  REQUIRE(mean_channel_error <= 2.0);
  REQUIRE(changed_ratio <= 0.05);
}

TEST_CASE("fixed seed selects deterministic variation layers") {
  mascotrender::Engine engine;

  auto seed_one = engine.render(example_request("sample.json"));
  REQUIRE(seed_one);
  auto seed_one_again = engine.render(example_request("sample.json"));
  REQUIRE(seed_one_again);
  auto seed_two = engine.render(example_request("sample-seed-2.json"));
  REQUIRE(seed_two);

  REQUIRE(seed_one.value().bytes == seed_one_again.value().bytes);
  REQUIRE(seed_one.value().bytes != seed_two.value().bytes);

  const auto one_pixels = decode(seed_one.value());
  const auto two_pixels = decode(seed_two.value());
  REQUIRE(pixel_at(one_pixels, 512, 87, 247).alpha == 0);
  REQUIRE(pixel_at(one_pixels, 512, 425, 247).alpha == 255);
  REQUIRE(pixel_at(two_pixels, 512, 87, 247).alpha == 255);
  REQUIRE(pixel_at(two_pixels, 512, 425, 247).alpha == 0);
  REQUIRE(pixel_at(one_pixels, 512, 185, 100).alpha == 255);
  REQUIRE(pixel_at(two_pixels, 512, 327, 100).alpha == 255);
}

TEST_CASE("omitted seed has a stable FNV-1a and SplitMix64 result") {
  mascotrender::Engine engine;

  auto first = engine.render(example_request("derived-seed.json"));
  REQUIRE(first);
  auto second = engine.render(example_request("derived-seed.json"));
  REQUIRE(second);
  REQUIRE(first.value().bytes == second.value().bytes);

  // v1's known derived seed is 1660711862001025047 and selects choice 0.
  const auto pixels = decode(first.value());
  REQUIRE(pixel_at(pixels, 512, 87, 247).alpha == 255);
  REQUIRE(pixel_at(pixels, 512, 425, 247).alpha == 0);
}

TEST_CASE("named expressions and poses change declared layer selections") {
  mascotrender::Engine engine;

  auto happy_front = engine.render(example_request("sample.json"));
  REQUIRE(happy_front);
  auto sleepy_round = engine.render(example_request("sleepy-round.json"));
  REQUIRE(sleepy_round);
  auto surprised_front = engine.render(example_request("surprised-front.json"));
  REQUIRE(surprised_front);

  REQUIRE(happy_front.value().bytes != sleepy_round.value().bytes);
  REQUIRE(happy_front.value().bytes != surprised_front.value().bytes);

  const auto happy_pixels = decode(happy_front.value());
  const auto sleepy_pixels = decode(sleepy_round.value());
  REQUIRE(pixel_at(happy_pixels, 512, 185, 100).alpha == 255);
  REQUIRE(pixel_at(sleepy_pixels, 512, 185, 100).alpha == 0);
  REQUIRE(pixel_at(happy_pixels, 512, 209, 257).red < 100);
  REQUIRE(pixel_at(sleepy_pixels, 512, 209, 257).red > 180);
}

TEST_CASE("unknown named selection reports source and JSON location") {
  mascotrender::Engine engine;
  auto request = example_request();
  request.sticker_file =
      source_root / "tests" / "fixtures" / "unknown-expression-sticker.json";

  auto result = engine.render(request);
  REQUIRE_FALSE(result);
  REQUIRE(result.error().code == mascotrender::ErrorCode::invalid_document);
  REQUIRE(result.error().source == request.sticker_file.string());
  REQUIRE(result.error().location == "$.expression");
}

TEST_CASE("pack loader rejects a layer path outside the pack") {
  mascotrender::Engine engine;
  auto request = example_request();
  request.pack_file =
      source_root / "tests" / "fixtures" / "traversal-pack.json";
  request.sticker_file =
      source_root / "tests" / "fixtures" / "traversal-sticker.json";

  auto result = engine.render(request);
  REQUIRE_FALSE(result);
  REQUIRE(result.error().code == mascotrender::ErrorCode::invalid_document);
  REQUIRE(result.error().source == request.pack_file.string());
  REQUIRE(result.error().location == "$.layers[0].source");
}

TEST_CASE("pack loader rejects a font path outside the pack") {
  mascotrender::Engine engine;
  auto request = example_request();
  request.pack_file =
      source_root / "tests" / "fixtures" / "traversal-font-pack.json";
  request.sticker_file =
      source_root / "tests" / "fixtures" / "traversal-font-sticker.json";

  auto result = engine.render(request);
  REQUIRE_FALSE(result);
  REQUIRE(result.error().code == mascotrender::ErrorCode::invalid_document);
  REQUIRE(result.error().source == request.pack_file.string());
  REQUIRE(result.error().location == "$.fonts[0].source");
}

TEST_CASE("unknown sticker text style reports its JSON location") {
  mascotrender::Engine engine;
  auto request = example_request();
  request.sticker_file =
      source_root / "tests" / "fixtures" / "unknown-text-style-sticker.json";

  auto result = engine.render(request);
  REQUIRE_FALSE(result);
  REQUIRE(result.error().code == mascotrender::ErrorCode::invalid_document);
  REQUIRE(result.error().source == request.sticker_file.string());
  REQUIRE(result.error().location == "$.text.style");
}

TEST_CASE("unknown sticker text slot reports its JSON location") {
  mascotrender::Engine engine;
  auto request = example_request();
  request.sticker_file =
      source_root / "tests" / "fixtures" / "unknown-text-slot-sticker.json";

  auto result = engine.render(request);
  REQUIRE_FALSE(result);
  REQUIRE(result.error().code == mascotrender::ErrorCode::invalid_document);
  REQUIRE(result.error().source == request.sticker_file.string());
  REQUIRE(result.error().location == "$.text.placement");
}

TEST_CASE("unknown animation overlay reports its JSON location") {
  mascotrender::Engine engine;
  auto request = example_request();
  request.sticker_file = source_root / "tests" / "fixtures" /
                         "unknown-animation-overlay-sticker.json";

  auto result = engine.render(request);
  REQUIRE_FALSE(result);
  REQUIRE(result.error().code == mascotrender::ErrorCode::invalid_document);
  REQUIRE(result.error().source == request.sticker_file.string());
  REQUIRE(result.error().location == "$.animation.overlays[0]");
}

TEST_CASE("unknown animation node target reports its JSON location") {
  mascotrender::Engine engine;
  auto request = robot_2_5d_request();
  request.sticker_file = source_root / "tests" / "fixtures" /
                         "unknown-animation-target-sticker.json";

  auto result = engine.render(request);
  REQUIRE_FALSE(result);
  REQUIRE(result.error().code == mascotrender::ErrorCode::invalid_document);
  REQUIRE(result.error().source == request.sticker_file.string());
  REQUIRE(result.error().location == "$.animation.tracks[0].target");
}
