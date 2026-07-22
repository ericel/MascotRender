#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <string_view>

#include <mascotrender/mascotrender.hpp>

int main(int argc, char **argv) {
  if (std::string_view{mascotrender::version_string()} != "0.9.0") {
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
  const auto &image = result.value();
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

  const auto robot = resources / "examples" / "robot-2_5d";
  const mascotrender::RenderRequest layered_request{
      robot / "pack.json", robot / "stickers" / "flat.json", {}};
  const mascotrender::RenderRequest flat_request{
      robot / "pack-flat.json", robot / "stickers" / "flat.json", {}};
  const mascotrender::RenderRequest parallax_request{
      robot / "pack.json", robot / "stickers" / "parallax-right.json", {}};
  const mascotrender::RenderRequest animated_request{
      robot / "pack.json", robot / "stickers" / "animated-hop.json", {}};
  auto layered = engine.render(layered_request);
  auto flat = engine.render(flat_request);
  auto parallax = engine.render(parallax_request);
  auto animated = engine.render(animated_request);
  if (!layered || !flat || !parallax || !animated) {
    return 6;
  }
  if (layered.value().bytes != flat.value().bytes ||
      layered.value().bytes == parallax.value().bytes ||
      animated.value().bytes == layered.value().bytes) {
    return 7;
  }
  const auto contains_chunk = [](const auto &bytes, std::string_view chunk) {
    if (bytes.size() < chunk.size()) {
      return false;
    }
    for (std::size_t offset = 0; offset <= bytes.size() - chunk.size();
         ++offset) {
      bool matches = true;
      for (std::size_t index = 0; index < chunk.size(); ++index) {
        matches = matches &&
                  std::to_integer<char>(bytes[offset + index]) == chunk[index];
      }
      if (matches) {
        return true;
      }
    }
    return false;
  };

  const auto calendar =
      resources / "art" / "calendar-pop-v1" / "calendar-pop-v1";
  const mascotrender::RenderRequest calendar_request{
      calendar / "pack.json", calendar / "stickers" / "monday.json", {}};
  auto calendar_result = engine.render(calendar_request);
  if (!calendar_result || calendar_result.value().width != 512 ||
      calendar_result.value().height != 512) {
    return 8;
  }
  if (!contains_chunk(calendar_result.value().bytes, "ANIM") ||
      !contains_chunk(calendar_result.value().bytes, "ANMF")) {
    return 9;
  }

  const auto congratulations =
      resources / "art" / "congratulations-pop-v1" / "congratulations-pop-v1";
  const mascotrender::RenderRequest congratulations_request{
      congratulations / "pack.json",
      congratulations / "stickers" / "congrats.json",
      {}};
  auto congratulations_result = engine.render(congratulations_request);
  if (!congratulations_result || congratulations_result.value().width != 512 ||
      congratulations_result.value().height != 512) {
    return 10;
  }
  if (!contains_chunk(congratulations_result.value().bytes, "ANIM") ||
      !contains_chunk(congratulations_result.value().bytes, "ANMF")) {
    return 11;
  }

  const auto workday =
      resources / "art" / "workday-reactions-v1" / "workday-reactions-v1";
  const mascotrender::RenderRequest workday_request{
      workday / "pack.json", workday / "stickers" / "on-it.json", {}};
  auto workday_result = engine.render(workday_request);
  if (!workday_result || workday_result.value().width != 512 ||
      workday_result.value().height != 512) {
    return 12;
  }
  if (!contains_chunk(workday_result.value().bytes, "ANIM") ||
      !contains_chunk(workday_result.value().bytes, "ANMF")) {
    return 13;
  }

  const auto education = resources / "art" /
                         "education-wise-owl-illustrated-v2" /
                         "education-wise-owl-illustrated-v2";
  const mascotrender::RenderRequest education_request{
      education / "pack.json", education / "stickers" / "study-time.json", {}};
  auto education_result = engine.render(education_request);
  if (!education_result || education_result.value().width != 512 ||
      education_result.value().height != 512) {
    return 14;
  }
  if (!contains_chunk(education_result.value().bytes, "ANIM") ||
      !contains_chunk(education_result.value().bytes, "ANMF")) {
    return 15;
  }

  if (!contains_chunk(animated.value().bytes, "ANIM") ||
      !contains_chunk(animated.value().bytes, "ANMF")) {
    return 16;
  }

  std::ofstream output{"mascotrender-package-test.webp", std::ios::binary};
  output.write(reinterpret_cast<const char *>(image.bytes.data()),
               static_cast<std::streamsize>(image.bytes.size()));
  return output ? 0 : 17;
}
