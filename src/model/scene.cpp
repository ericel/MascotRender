#include "model/scene.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <map>
#include <nlohmann/json.hpp>
#include <optional>
#include <set>
#include <sstream>
#include <string>
#include <string_view>
#include <system_error>
#include <utility>
#include <vector>

namespace mascotrender::detail {
namespace {

using Json = nlohmann::json;

struct Layer {
  std::filesystem::path source;
  std::int32_t z{};
  std::optional<Rect> collision_bounds;
};

struct Font {
  std::filesystem::path source;
};

struct TextStyle {
  std::string font;
  Rect safe_area;
  float min_font_size{};
  float max_font_size{};
  std::uint32_t max_lines{};
  Color fill;
  Color outline;
  float outline_width{};
};

[[nodiscard]] Error document_error(std::string message,
                                   const std::filesystem::path &source = {},
                                   std::string location = {}) {
  return Error{ErrorCode::invalid_document, std::move(message), source.string(),
               std::move(location)};
}

[[nodiscard]] Error io_error(std::string message,
                             const std::filesystem::path &source) {
  return Error{ErrorCode::io_error, std::move(message), source.string(), {}};
}

[[nodiscard]] Result<Json> read_json(const std::filesystem::path &path) {
  std::ifstream input{path, std::ios::binary};
  if (!input) {
    return Result<Json>::failure(io_error("Could not open JSON file", path));
  }

  std::ostringstream contents;
  contents << input.rdbuf();
  if (!input.good() && !input.eof()) {
    return Result<Json>::failure(io_error("Could not read JSON file", path));
  }

  try {
    return Result<Json>::success(Json::parse(contents.str()));
  } catch (const Json::exception &exception) {
    return Result<Json>::failure(document_error(
        "Invalid JSON: " + std::string{exception.what()}, path, "$"));
  }
}

[[nodiscard]] bool is_descendant(const std::filesystem::path &root,
                                 const std::filesystem::path &candidate) {
  auto root_it = root.begin();
  auto candidate_it = candidate.begin();
  while (root_it != root.end() && candidate_it != candidate.end()) {
    if (*root_it != *candidate_it) {
      return false;
    }
    ++root_it;
    ++candidate_it;
  }
  return root_it == root.end();
}

[[nodiscard]] Result<std::filesystem::path>
resolve_asset(const std::filesystem::path &root,
              const std::string &asset_source,
              const std::filesystem::path &pack_file, std::string location,
              std::string_view expected_extension, std::string_view kind) {
  const std::filesystem::path relative{asset_source};
  if (relative.empty() || relative.is_absolute() || relative.has_root_name() ||
      asset_source.find("://") != std::string::npos ||
      relative.extension() != expected_extension) {
    return Result<std::filesystem::path>::failure(document_error(
        std::string{kind} + " must be a relative local " +
            std::string{expected_extension} + " path: " + asset_source,
        pack_file, std::move(location)));
  }

  std::error_code error;
  const auto resolved = std::filesystem::canonical(root / relative, error);
  if (error) {
    return Result<std::filesystem::path>::failure(
        Error{ErrorCode::io_error,
              "Could not resolve " + std::string{kind} + ": " + asset_source,
              pack_file.string(), std::move(location)});
  }
  if (!is_descendant(root, resolved)) {
    return Result<std::filesystem::path>::failure(document_error(
        std::string{kind} + " escapes the pack directory: " + asset_source,
        pack_file, std::move(location)));
  }
  return Result<std::filesystem::path>::success(resolved);
}

[[nodiscard]] std::uint64_t fnv1a_append(std::uint64_t hash,
                                         std::string_view value) {
  constexpr std::uint64_t prime = 1099511628211ULL;
  for (const unsigned char character : value) {
    hash ^= character;
    hash *= prime;
  }
  hash ^= 0U;
  hash *= prime;
  return hash;
}

[[nodiscard]] std::uint64_t derived_seed(std::string_view pack_id,
                                         std::string_view sticker_id) {
  constexpr std::uint64_t offset_basis = 14695981039346656037ULL;
  return fnv1a_append(fnv1a_append(offset_basis, pack_id), sticker_id);
}

[[nodiscard]] std::uint64_t splitmix64(std::uint64_t &state) {
  state += 0x9e3779b97f4a7c15ULL;
  auto value = state;
  value = (value ^ (value >> 30U)) * 0xbf58476d1ce4e5b9ULL;
  value = (value ^ (value >> 27U)) * 0x94d049bb133111ebULL;
  return value ^ (value >> 31U);
}

[[nodiscard]] Result<Rect>
parse_rect(const Json &value, std::uint32_t canvas_width,
           std::uint32_t canvas_height, const std::filesystem::path &source,
           std::string location, std::string_view kind) {
  const Rect area{value.at("x").get<float>(), value.at("y").get<float>(),
                  value.at("width").get<float>(),
                  value.at("height").get<float>()};
  if (!std::isfinite(area.x) || !std::isfinite(area.y) ||
      !std::isfinite(area.width) || !std::isfinite(area.height) ||
      area.x < 0.0F || area.y < 0.0F || area.width <= 0.0F ||
      area.height <= 0.0F || area.x + area.width > canvas_width ||
      area.y + area.height > canvas_height) {
    return Result<Rect>::failure(document_error(
        std::string{kind} + " must be finite, positive, and inside the canvas",
        source, std::move(location)));
  }
  return Result<Rect>::success(area);
}

[[nodiscard]] Result<Scene>
parse_scene(const Json &pack, const Json &sticker,
            const std::filesystem::path &pack_file,
            const std::filesystem::path &sticker_file) {
  try {
    if (pack.at("schema_version").get<std::uint32_t>() != 1U) {
      return Result<Scene>::failure(document_error(
          "Only schema_version 1 is supported", pack_file, "$.schema_version"));
    }
    if (sticker.at("schema_version").get<std::uint32_t>() != 1U) {
      return Result<Scene>::failure(
          document_error("Only schema_version 1 is supported", sticker_file,
                         "$.schema_version"));
    }

    const auto pack_id = pack.at("pack_id").get<std::string>();
    const auto sticker_id = sticker.at("sticker_id").get<std::string>();
    if (pack_id.empty() || sticker_id.empty() ||
        sticker.at("pack_id").get<std::string>() != pack_id) {
      return Result<Scene>::failure(
          document_error("Sticker pack_id does not match the pack",
                         sticker_file, "$.pack_id"));
    }

    Scene scene;
    scene.width = pack.at("canvas").at("width").get<std::uint32_t>();
    scene.height = pack.at("canvas").at("height").get<std::uint32_t>();
    if (scene.width == 0 || scene.height == 0 || scene.width > 4096 ||
        scene.height > 4096) {
      return Result<Scene>::failure(
          document_error("Pack canvas dimensions must be between 1 and 4096",
                         pack_file, "$.canvas"));
    }

    const auto &provenance = pack.at("provenance");
    if (provenance.at("creator").get<std::string>().empty() ||
        provenance.at("license").get<std::string>().empty() ||
        provenance.at("source").get<std::string>().empty()) {
      return Result<Scene>::failure(
          document_error("Pack provenance fields must be non-empty", pack_file,
                         "$.provenance"));
    }

    const auto validate_points =
        [&](const Json &points,
            const std::string &location) -> std::optional<Error> {
      for (auto item = points.begin(); item != points.end(); ++item) {
        const auto x = item.value().at("x").get<double>();
        const auto y = item.value().at("y").get<double>();
        if (!std::isfinite(x) || !std::isfinite(y) || x < 0.0 || y < 0.0 ||
            x > scene.width || y > scene.height) {
          return document_error(
              "Anchor and pivot points must be finite and inside the "
              "canvas",
              pack_file, location + "." + item.key());
        }
      }
      return std::nullopt;
    };
    if (auto error = validate_points(pack.at("anchors"), "$.anchors")) {
      return Result<Scene>::failure(std::move(*error));
    }
    if (auto error = validate_points(pack.at("pivots"), "$.pivots")) {
      return Result<Scene>::failure(std::move(*error));
    }

    const auto pack_root = pack_file.parent_path();

    std::map<std::string, Font, std::less<>> fonts;
    if (pack.contains("fonts")) {
      std::size_t font_index = 0;
      for (const auto &item : pack.at("fonts")) {
        const auto location = "$.fonts[" + std::to_string(font_index) + "]";
        const auto id = item.at("id").get<std::string>();
        if (id.empty() || fonts.contains(id)) {
          return Result<Scene>::failure(
              document_error("Pack font IDs must be non-empty and unique",
                             pack_file, location + ".id"));
        }

        const auto source = item.at("source").get<std::string>();
        auto resolved =
            resolve_asset(pack_root, source, pack_file, location + ".source",
                          ".ttf", "Font source");
        if (!resolved) {
          return Result<Scene>::failure(resolved.error());
        }

        const auto license = item.at("license").get<std::string>();
        auto resolved_license =
            resolve_asset(pack_root, license, pack_file, location + ".license",
                          ".txt", "Font license");
        if (!resolved_license) {
          return Result<Scene>::failure(resolved_license.error());
        }

        fonts.emplace(id, Font{std::move(resolved).value()});
        ++font_index;
      }
    }

    std::map<std::string, Rect, std::less<>> text_slots;
    if (pack.contains("text_slots")) {
      for (auto item = pack.at("text_slots").begin();
           item != pack.at("text_slots").end(); ++item) {
        const auto location = "$.text_slots." + item.key();
        if (item.key().empty()) {
          return Result<Scene>::failure(document_error(
              "Text slot IDs must be non-empty", pack_file, location));
        }
        auto area = parse_rect(item.value(), scene.width, scene.height,
                               pack_file, location, "Text slot");
        if (!area) {
          return Result<Scene>::failure(area.error());
        }
        text_slots.emplace(item.key(), std::move(area).value());
      }
    }

    std::vector<Rect> avoid_regions;
    if (pack.contains("avoid_regions")) {
      std::set<std::string, std::less<>> names;
      std::size_t index = 0;
      for (const auto &item : pack.at("avoid_regions")) {
        const auto location = "$.avoid_regions[" + std::to_string(index) + "]";
        const auto name = item.at("name").get<std::string>();
        if (name.empty() || !names.insert(name).second) {
          return Result<Scene>::failure(
              document_error("Avoid-region names must be non-empty and unique",
                             pack_file, location + ".name"));
        }
        auto area = parse_rect(item, scene.width, scene.height, pack_file,
                               location, "Avoid region");
        if (!area) {
          return Result<Scene>::failure(area.error());
        }
        avoid_regions.push_back(std::move(area).value());
        ++index;
      }
    }

    float text_clearance = 0.0F;
    if (pack.contains("text_clearance")) {
      text_clearance = pack.at("text_clearance").get<float>();
      if (!std::isfinite(text_clearance) || text_clearance < 0.0F ||
          text_clearance > 128.0F) {
        return Result<Scene>::failure(document_error(
            "Text clearance must be finite and between 0 and 128", pack_file,
            "$.text_clearance"));
      }
    }

    std::map<std::string, TextStyle, std::less<>> text_styles;
    if (pack.contains("text_styles")) {
      for (auto item = pack.at("text_styles").begin();
           item != pack.at("text_styles").end(); ++item) {
        const auto location = "$.text_styles." + item.key();
        if (item.key().empty()) {
          return Result<Scene>::failure(document_error(
              "Text style IDs must be non-empty", pack_file, location));
        }

        const auto font_id = item.value().at("font").get<std::string>();
        if (!fonts.contains(font_id)) {
          return Result<Scene>::failure(
              document_error("Unknown font reference: " + font_id, pack_file,
                             location + ".font"));
        }

        auto parsed_safe_area =
            parse_rect(item.value().at("safe_area"), scene.width, scene.height,
                       pack_file, location + ".safe_area", "Text safe area");
        if (!parsed_safe_area) {
          return Result<Scene>::failure(parsed_safe_area.error());
        }
        const auto safe_area = std::move(parsed_safe_area).value();

        const auto min_size = item.value().at("min_font_size").get<float>();
        const auto max_size = item.value().at("max_font_size").get<float>();
        if (!std::isfinite(min_size) || !std::isfinite(max_size) ||
            min_size <= 0.0F || max_size < min_size || max_size > 512.0F) {
          return Result<Scene>::failure(
              document_error("Text font sizes must be finite, positive, "
                             "ordered, and at most 512",
                             pack_file, location));
        }

        const auto max_lines =
            item.value().at("max_lines").get<std::uint32_t>();
        if (max_lines == 0U || max_lines > 3U) {
          return Result<Scene>::failure(
              document_error("Text max_lines must be between 1 and 3",
                             pack_file, location + ".max_lines"));
        }

        const auto &fill = item.value().at("fill");
        const auto red = fill.at("r").get<std::uint32_t>();
        const auto green = fill.at("g").get<std::uint32_t>();
        const auto blue = fill.at("b").get<std::uint32_t>();
        if (red > 255U || green > 255U || blue > 255U) {
          return Result<Scene>::failure(
              document_error("Text fill channels must be between 0 and 255",
                             pack_file, location + ".fill"));
        }

        Color outline{};
        float outline_width = 0.0F;
        if (item.value().contains("outline")) {
          const auto &configured = item.value().at("outline");
          outline_width = configured.at("width").get<float>();
          if (!std::isfinite(outline_width) || outline_width < 0.0F ||
              outline_width > 32.0F) {
            return Result<Scene>::failure(document_error(
                "Text outline width must be finite and between 0 "
                "and 32",
                pack_file, location + ".outline.width"));
          }
          const auto &color = configured.at("color");
          const auto outline_red = color.at("r").get<std::uint32_t>();
          const auto outline_green = color.at("g").get<std::uint32_t>();
          const auto outline_blue = color.at("b").get<std::uint32_t>();
          if (outline_red > 255U || outline_green > 255U ||
              outline_blue > 255U) {
            return Result<Scene>::failure(document_error(
                "Text outline channels must be between 0 and 255", pack_file,
                location + ".outline.color"));
          }
          outline = Color{static_cast<std::uint8_t>(outline_red),
                          static_cast<std::uint8_t>(outline_green),
                          static_cast<std::uint8_t>(outline_blue)};
        }

        text_styles.emplace(item.key(),
                            TextStyle{font_id, safe_area, min_size, max_size,
                                      max_lines,
                                      Color{static_cast<std::uint8_t>(red),
                                            static_cast<std::uint8_t>(green),
                                            static_cast<std::uint8_t>(blue)},
                                      outline, outline_width});
      }
    }

    std::map<std::string, Layer, std::less<>> available;
    std::set<std::int32_t> z_values;
    std::size_t layer_index = 0;
    for (const auto &item : pack.at("layers")) {
      const auto location = "$.layers[" + std::to_string(layer_index) + "]";
      const auto id = item.at("id").get<std::string>();
      const auto source = item.at("source").get<std::string>();
      const auto z = item.at("z").get<std::int32_t>();
      if (id.empty() || available.contains(id)) {
        return Result<Scene>::failure(
            document_error("Pack layer IDs must be non-empty and unique",
                           pack_file, location + ".id"));
      }
      if (!z_values.insert(z).second) {
        return Result<Scene>::failure(document_error(
            "Pack layer z values must be unique", pack_file, location + ".z"));
      }
      auto resolved =
          resolve_asset(pack_root, source, pack_file, location + ".source",
                        ".svg", "Layer source");
      if (!resolved) {
        return Result<Scene>::failure(resolved.error());
      }
      std::optional<Rect> collision_bounds;
      if (item.contains("collision_bounds")) {
        auto parsed = parse_rect(item.at("collision_bounds"), scene.width,
                                 scene.height, pack_file,
                                 location + ".collision_bounds",
                                 "Layer collision bounds");
        if (!parsed) {
          return Result<Scene>::failure(parsed.error());
        }
        collision_bounds = std::move(parsed).value();
      }
      available.emplace(
          id, Layer{std::move(resolved).value(), z, collision_bounds});
      ++layer_index;
    }

    std::set<std::string, std::less<>> selected_ids;
    const auto select =
        [&](const Json &ids, const std::filesystem::path &source,
            const std::string &location) -> std::optional<Error> {
      std::size_t index = 0;
      for (const auto &item : ids) {
        const auto id = item.get<std::string>();
        if (!available.contains(id)) {
          return document_error("Unknown layer reference: " + id, source,
                                location + "[" + std::to_string(index) + "]");
        }
        selected_ids.insert(id);
        ++index;
      }
      return std::nullopt;
    };

    if (auto error =
            select(pack.at("base_layers"), pack_file, "$.base_layers")) {
      return Result<Scene>::failure(std::move(*error));
    }

    const auto expression = sticker.at("expression").get<std::string>();
    const auto &expressions = pack.at("expressions");
    if (!expressions.contains(expression)) {
      return Result<Scene>::failure(document_error(
          "Unknown expression: " + expression, sticker_file, "$.expression"));
    }
    if (auto error = select(expressions.at(expression), pack_file,
                            "$.expressions." + expression)) {
      return Result<Scene>::failure(std::move(*error));
    }

    const auto pose = sticker.at("pose").get<std::string>();
    const auto &poses = pack.at("poses");
    if (!poses.contains(pose)) {
      return Result<Scene>::failure(
          document_error("Unknown pose: " + pose, sticker_file, "$.pose"));
    }
    if (auto error = select(poses.at(pose), pack_file, "$.poses." + pose)) {
      return Result<Scene>::failure(std::move(*error));
    }

    if (sticker.contains("layers")) {
      if (auto error = select(sticker.at("layers"), sticker_file, "$.layers")) {
        return Result<Scene>::failure(std::move(*error));
      }
    }

    auto random_state = sticker.contains("seed")
                            ? sticker.at("seed").get<std::uint64_t>()
                            : derived_seed(pack_id, sticker_id);
    if (pack.contains("variation_groups")) {
      std::set<std::string, std::less<>> group_ids;
      std::size_t group_index = 0;
      for (const auto &group : pack.at("variation_groups")) {
        const auto location =
            "$.variation_groups[" + std::to_string(group_index) + "]";
        const auto group_id = group.at("id").get<std::string>();
        if (group_id.empty() || !group_ids.insert(group_id).second) {
          return Result<Scene>::failure(
              document_error("Variation group IDs must be non-empty and unique",
                             pack_file, location + ".id"));
        }
        const auto &choices = group.at("choices");
        if (choices.empty()) {
          return Result<Scene>::failure(
              document_error("Variation group must contain at least one choice",
                             pack_file, location + ".choices"));
        }
        const auto choice_index =
            static_cast<std::size_t>(splitmix64(random_state) % choices.size());
        if (auto error = select(choices.at(choice_index), pack_file,
                                location + ".choices[" +
                                    std::to_string(choice_index) + "]")) {
          return Result<Scene>::failure(std::move(*error));
        }
        ++group_index;
      }
    }

    if (selected_ids.empty()) {
      return Result<Scene>::failure(document_error(
          "Resolved sticker contains no layers", sticker_file, "$"));
    }

    std::vector<Layer> selected;
    selected.reserve(selected_ids.size());
    for (const auto &id : selected_ids) {
      const auto &layer = available.at(id);
      selected.push_back(layer);
    }
    std::sort(selected.begin(), selected.end(),
              [](const auto &left, const auto &right) {
                return left.z < right.z;
              });
    scene.layers.reserve(selected.size());
    for (auto &layer : selected) {
      scene.layers.push_back(std::move(layer.source));
      if (layer.collision_bounds) {
        const auto &bounds = *layer.collision_bounds;
        const auto left = std::max(0.0F, bounds.x - text_clearance);
        const auto top = std::max(0.0F, bounds.y - text_clearance);
        const auto right = std::min(static_cast<float>(scene.width),
                                    bounds.x + bounds.width + text_clearance);
        const auto bottom = std::min(static_cast<float>(scene.height),
                                     bounds.y + bounds.height + text_clearance);
        avoid_regions.push_back(
            Rect{left, top, right - left, bottom - top});
      }
    }

    if (sticker.contains("text")) {
      const auto &text = sticker.at("text");
      const auto content = text.at("content").get<std::string>();
      const auto style_id = text.at("style").get<std::string>();
      if (content.empty() || content.size() > 280U ||
          content.find('\0') != std::string::npos) {
        return Result<Scene>::failure(document_error(
            "Sticker text must contain 1 to 280 UTF-8 bytes and no NUL",
            sticker_file, "$.text.content"));
      }
      if (!text_styles.contains(style_id)) {
        return Result<Scene>::failure(document_error(
            "Unknown text style: " + style_id, sticker_file, "$.text.style"));
      }

      const auto &style = text_styles.at(style_id);
      std::vector<Rect> candidate_areas;
      bool auto_placement = false;
      if (!text.contains("placement")) {
        if (text.contains("preferred_slots")) {
          return Result<Scene>::failure(
              document_error("preferred_slots requires auto placement",
                             sticker_file, "$.text.preferred_slots"));
        }
        candidate_areas.push_back(style.safe_area);
      } else {
        const auto placement = text.at("placement").get<std::string>();
        if (placement == "auto") {
          auto_placement = true;
          if (text.contains("preferred_slots")) {
            std::set<std::string, std::less<>> seen;
            std::size_t index = 0;
            for (const auto &candidate : text.at("preferred_slots")) {
              const auto slot = candidate.get<std::string>();
              if (!text_slots.contains(slot)) {
                return Result<Scene>::failure(document_error(
                    "Unknown text slot: " + slot, sticker_file,
                    "$.text.preferred_slots[" + std::to_string(index) + "]"));
              }
              if (!seen.insert(slot).second) {
                return Result<Scene>::failure(document_error(
                    "Preferred text slots must be unique", sticker_file,
                    "$.text.preferred_slots[" + std::to_string(index) + "]"));
              }
              candidate_areas.push_back(text_slots.at(slot));
              ++index;
            }
          } else {
            for (const auto &[id, area] : text_slots) {
              static_cast<void>(id);
              candidate_areas.push_back(area);
            }
          }
          if (candidate_areas.empty()) {
            return Result<Scene>::failure(
                document_error("Auto text placement requires at "
                               "least one pack text slot",
                               sticker_file, "$.text.placement"));
          }
        } else {
          if (text.contains("preferred_slots")) {
            return Result<Scene>::failure(document_error(
                "preferred_slots is only valid with auto placement",
                sticker_file, "$.text.preferred_slots"));
          }
          if (!text_slots.contains(placement)) {
            return Result<Scene>::failure(
                document_error("Unknown text slot: " + placement, sticker_file,
                               "$.text.placement"));
          }
          candidate_areas.push_back(text_slots.at(placement));
        }
      }
      scene.text.push_back(
          TextBlock{fonts.at(style.font).source, content,
                    std::move(candidate_areas), avoid_regions, auto_placement,
                    style.min_font_size, style.max_font_size, style.max_lines,
                    style.fill, style.outline, style.outline_width});
    }

    if (sticker.contains("animation")) {
      const auto &configured = sticker.at("animation");
      const auto duration_ms =
          configured.at("duration_ms").get<std::uint32_t>();
      const auto fps = configured.at("fps").get<std::uint32_t>();
      const auto frame_count =
          (static_cast<std::uint64_t>(duration_ms) * fps + 999U) / 1000U;
      if (duration_ms < 100U || duration_ms > 10000U) {
        return Result<Scene>::failure(document_error(
            "Animation duration_ms must be between 100 and 10000", sticker_file,
            "$.animation.duration_ms"));
      }
      if (fps == 0U || fps > 30U || frame_count < 2U || frame_count > 300U) {
        return Result<Scene>::failure(
            document_error("Animation fps must produce between 2 and 300 "
                           "frames at 1 to 30 FPS",
                           sticker_file, "$.animation.fps"));
      }

      const auto loop_name = configured.at("loop").get<std::string>();
      AnimationLoop loop;
      if (loop_name == "once") {
        loop = AnimationLoop::once;
      } else if (loop_name == "loop") {
        loop = AnimationLoop::loop;
      } else if (loop_name == "ping_pong") {
        loop = AnimationLoop::ping_pong;
      } else if (loop_name == "hold_last_frame") {
        loop = AnimationLoop::hold_last_frame;
      } else {
        return Result<Scene>::failure(
            document_error("Unknown animation loop mode: " + loop_name,
                           sticker_file, "$.animation.loop"));
      }

      bool body_bounce = false;
      bool text_pop = false;
      std::set<std::string, std::less<>> overlays;
      std::size_t index = 0;
      const auto &configured_overlays = configured.at("overlays");
      if (configured_overlays.empty()) {
        return Result<Scene>::failure(
            document_error("Animation overlays must not be empty", sticker_file,
                           "$.animation.overlays"));
      }
      for (const auto &item : configured_overlays) {
        const auto name = item.get<std::string>();
        const auto location =
            "$.animation.overlays[" + std::to_string(index) + "]";
        if (!overlays.insert(name).second) {
          return Result<Scene>::failure(document_error(
              "Animation overlays must be unique", sticker_file, location));
        }
        if (name == "body_bounce") {
          body_bounce = true;
        } else if (name == "text_pop") {
          text_pop = true;
        } else {
          return Result<Scene>::failure(document_error(
              "Unknown animation overlay: " + name, sticker_file, location));
        }
        ++index;
      }
      if (text_pop && scene.text.empty()) {
        return Result<Scene>::failure(
            document_error("text_pop requires sticker text", sticker_file,
                           "$.animation.overlays"));
      }
      scene.animation =
          AnimationSpec{duration_ms, fps, loop, body_bounce, text_pop};
    }
    return Result<Scene>::success(std::move(scene));
  } catch (const Json::exception &exception) {
    return Result<Scene>::failure(
        document_error("Pack or sticker does not match schema_version 1: " +
                           std::string{exception.what()},
                       {}, "$"));
  }
}

} // namespace

Result<Scene> load_scene(const std::filesystem::path &pack_file,
                         const std::filesystem::path &sticker_file) {
  if (pack_file.empty() || sticker_file.empty()) {
    return Result<Scene>::failure(
        Error{ErrorCode::invalid_argument,
              "Both pack_file and sticker_file are required",
              {},
              {}});
  }

  std::error_code error;
  const auto canonical_pack = std::filesystem::canonical(pack_file, error);
  if (error) {
    return Result<Scene>::failure(
        io_error("Could not resolve pack file", pack_file));
  }
  const auto canonical_sticker =
      std::filesystem::canonical(sticker_file, error);
  if (error) {
    return Result<Scene>::failure(
        io_error("Could not resolve sticker file", sticker_file));
  }

  auto pack = read_json(canonical_pack);
  if (!pack) {
    return Result<Scene>::failure(pack.error());
  }
  auto sticker = read_json(canonical_sticker);
  if (!sticker) {
    return Result<Scene>::failure(sticker.error());
  }
  return parse_scene(pack.value(), sticker.value(), canonical_pack,
                     canonical_sticker);
}

} // namespace mascotrender::detail
