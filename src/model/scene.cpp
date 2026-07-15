#include "model/scene.hpp"

#include <algorithm>
#include <charconv>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <functional>
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
  std::string id;
  std::filesystem::path source;
  std::vector<std::pair<std::uint32_t, std::filesystem::path>> lod_sources;
  std::int32_t z{};
  std::optional<Rect> collision_bounds;
  std::optional<std::string> parent;
  std::optional<std::string> pivot;
  float depth{};
  bool screen_space{};
  float x{};
  float y{};
  float rotation_degrees{};
  float scale_x{1.0F};
  float scale_y{1.0F};
  float opacity{1.0F};
  std::string location;
  AffineTransform world_transform;
  Point world_pivot;
  float world_depth{};
  float world_opacity{1.0F};
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

[[nodiscard]] AffineTransform multiply(const AffineTransform &left,
                                       const AffineTransform &right) {
  return AffineTransform{left.m11 * right.m11 + left.m12 * right.m21,
                         left.m11 * right.m12 + left.m12 * right.m22,
                         left.m21 * right.m11 + left.m22 * right.m21,
                         left.m21 * right.m12 + left.m22 * right.m22,
                         left.m11 * right.translate_x +
                             left.m12 * right.translate_y + left.translate_x,
                         left.m21 * right.translate_x +
                             left.m22 * right.translate_y + left.translate_y};
}

[[nodiscard]] AffineTransform local_transform(const Layer &layer,
                                              const Point &pivot) {
  constexpr float degrees_to_radians = 3.14159265358979323846F / 180.0F;
  const auto angle = layer.rotation_degrees * degrees_to_radians;
  const auto cosine = std::cos(angle);
  const auto sine = std::sin(angle);
  const auto m11 = cosine * layer.scale_x;
  const auto m12 = -sine * layer.scale_y;
  const auto m21 = sine * layer.scale_x;
  const auto m22 = cosine * layer.scale_y;
  return AffineTransform{m11,
                         m12,
                         m21,
                         m22,
                         layer.x + pivot.x - m11 * pivot.x - m12 * pivot.y,
                         layer.y + pivot.y - m21 * pivot.x - m22 * pivot.y};
}

[[nodiscard]] Point transform_point(const AffineTransform &transform,
                                    const Point &point) {
  return Point{transform.m11 * point.x + transform.m12 * point.y +
                   transform.translate_x,
               transform.m21 * point.x + transform.m22 * point.y +
                   transform.translate_y};
}

[[nodiscard]] Rect transform_rect(const Rect &rect,
                                  const AffineTransform &transform) {
  const Point corners[]{
      transform_point(transform, Point{rect.x, rect.y}),
      transform_point(transform, Point{rect.x + rect.width, rect.y}),
      transform_point(transform, Point{rect.x, rect.y + rect.height}),
      transform_point(transform,
                      Point{rect.x + rect.width, rect.y + rect.height})};
  auto left = corners[0].x;
  auto top = corners[0].y;
  auto right = corners[0].x;
  auto bottom = corners[0].y;
  for (const auto &corner : corners) {
    left = std::min(left, corner.x);
    top = std::min(top, corner.y);
    right = std::max(right, corner.x);
    bottom = std::max(bottom, corner.y);
  }
  return Rect{left, top, right - left, bottom - top};
}

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

    if (sticker.contains("view")) {
      scene.view_offset_x = sticker.at("view").at("x").get<float>();
      scene.view_offset_y = sticker.at("view").at("y").get<float>();
      if (!std::isfinite(scene.view_offset_x) ||
          !std::isfinite(scene.view_offset_y) ||
          std::abs(scene.view_offset_x) > 128.0F ||
          std::abs(scene.view_offset_y) > 128.0F) {
        return Result<Scene>::failure(document_error(
            "Sticker view offsets must be finite and between -128 and 128",
            sticker_file, "$.view"));
      }
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

    std::map<std::string, Point, std::less<>> anchors;
    for (auto item = pack.at("anchors").begin();
         item != pack.at("anchors").end(); ++item) {
      anchors.emplace(item.key(), Point{item.value().at("x").get<float>(),
                                        item.value().at("y").get<float>()});
    }

    std::map<std::string, Point, std::less<>> pivots;
    for (auto item = pack.at("pivots").begin(); item != pack.at("pivots").end();
         ++item) {
      pivots.emplace(item.key(), Point{item.value().at("x").get<float>(),
                                       item.value().at("y").get<float>()});
    }

    if (sticker.contains("camera")) {
      const auto &camera = sticker.at("camera");
      const auto framing = camera.at("framing").get<std::string>();
      const std::set<std::string, std::less<>> supported_framings{
          "face-closeup", "bust", "three-quarter", "full-body",
          "dynamic-full-body"};
      if (!supported_framings.contains(framing)) {
        return Result<Scene>::failure(document_error(
            "Unknown semantic camera framing: " + framing, sticker_file,
            "$.camera.framing"));
      }
      const auto target_name = camera.at("target").get<std::string>();
      if (!anchors.contains(target_name)) {
        return Result<Scene>::failure(document_error(
            "Unknown camera target anchor: " + target_name, sticker_file,
            "$.camera.target"));
      }
      const auto zoom = camera.at("zoom").get<float>();
      const auto offset_x = camera.value("offset_x", 0.0F);
      const auto offset_y = camera.value("offset_y", 0.0F);
      if (!std::isfinite(zoom) || zoom < 0.5F || zoom > 3.0F ||
          !std::isfinite(offset_x) || !std::isfinite(offset_y) ||
          std::abs(offset_x) > 512.0F || std::abs(offset_y) > 512.0F) {
        return Result<Scene>::failure(document_error(
            "Camera zoom must be 0.5 to 3.0 and offsets must be finite within "
            "+/-512",
            sticker_file, "$.camera"));
      }
      const auto target = anchors.at(target_name);
      const auto destination_x = static_cast<float>(scene.width) * 0.5F +
                                 offset_x;
      const auto destination_y = static_cast<float>(scene.height) * 0.5F +
                                 offset_y;
      scene.camera_transform =
          AffineTransform{zoom, 0.0F, 0.0F, zoom,
                          destination_x - zoom * target.x,
                          destination_y - zoom * target.y};
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
      std::vector<std::pair<std::uint32_t, std::filesystem::path>> lod_sources;
      if (item.contains("lod_sources")) {
        for (auto lod = item.at("lod_sources").begin();
             lod != item.at("lod_sources").end(); ++lod) {
          std::uint32_t maximum_dimension{};
          const auto *begin = lod.key().data();
          const auto *end = begin + lod.key().size();
          const auto [parsed_end, error] =
              std::from_chars(begin, end, maximum_dimension);
          if (error != std::errc{} || parsed_end != end ||
              maximum_dimension < 32U || maximum_dimension > 512U) {
            return Result<Scene>::failure(document_error(
                "LOD source keys must be maximum dimensions from 32 to 512",
                pack_file, location + ".lod_sources." + lod.key()));
          }
          const auto lod_source = lod.value().get<std::string>();
          auto resolved_lod = resolve_asset(
              pack_root, lod_source, pack_file,
              location + ".lod_sources." + lod.key(), ".svg",
              "Layer LOD source");
          if (!resolved_lod) {
            return Result<Scene>::failure(resolved_lod.error());
          }
          lod_sources.emplace_back(maximum_dimension,
                                   std::move(resolved_lod).value());
        }
        std::sort(lod_sources.begin(), lod_sources.end(),
                  [](const auto &left, const auto &right) {
                    return left.first < right.first;
                  });
      }
      std::optional<Rect> collision_bounds;
      if (item.contains("collision_bounds")) {
        auto parsed = parse_rect(
            item.at("collision_bounds"), scene.width, scene.height, pack_file,
            location + ".collision_bounds", "Layer collision bounds");
        if (!parsed) {
          return Result<Scene>::failure(parsed.error());
        }
        collision_bounds = std::move(parsed).value();
      }

      std::optional<std::string> parent;
      if (item.contains("parent")) {
        parent = item.at("parent").get<std::string>();
        if (parent->empty() || *parent == id) {
          return Result<Scene>::failure(
              document_error("Layer parent must name a different layer",
                             pack_file, location + ".parent"));
        }
      }

      std::optional<std::string> pivot;
      if (item.contains("pivot")) {
        pivot = item.at("pivot").get<std::string>();
        if (pivot->empty() || !pivots.contains(*pivot)) {
          return Result<Scene>::failure(
              document_error("Unknown layer pivot: " + *pivot, pack_file,
                             location + ".pivot"));
        }
      }

      const auto depth = item.value("depth", 0.0F);
      const auto screen_space = item.value("screen_space", false);
      if (screen_space && parent) {
        return Result<Scene>::failure(document_error(
            "Screen-space layers cannot inherit a character parent", pack_file,
            location + ".screen_space"));
      }
      float x = 0.0F;
      float y = 0.0F;
      float rotation_degrees = 0.0F;
      float scale_x = 1.0F;
      float scale_y = 1.0F;
      float opacity = 1.0F;
      if (item.contains("transform")) {
        const auto &transform = item.at("transform");
        x = transform.value("x", 0.0F);
        y = transform.value("y", 0.0F);
        rotation_degrees = transform.value("rotation_degrees", 0.0F);
        scale_x = transform.value("scale_x", 1.0F);
        scale_y = transform.value("scale_y", 1.0F);
        opacity = transform.value("opacity", 1.0F);
      }
      if (!std::isfinite(depth) || depth < -4.0F || depth > 4.0F) {
        return Result<Scene>::failure(
            document_error("Layer depth must be finite and between -4 and 4",
                           pack_file, location + ".depth"));
      }
      if (!std::isfinite(x) || !std::isfinite(y) || std::abs(x) > 4096.0F ||
          std::abs(y) > 4096.0F || !std::isfinite(rotation_degrees) ||
          std::abs(rotation_degrees) > 3600.0F || !std::isfinite(scale_x) ||
          !std::isfinite(scale_y) || scale_x <= 0.0F || scale_x > 100.0F ||
          scale_y <= 0.0F || scale_y > 100.0F || !std::isfinite(opacity) ||
          opacity < 0.0F || opacity > 1.0F) {
        return Result<Scene>::failure(document_error(
            "Layer transform values are outside supported finite bounds",
            pack_file, location + ".transform"));
      }

      available.emplace(id, Layer{id, std::move(resolved).value(),
                                  std::move(lod_sources), z,
                                  collision_bounds, parent, pivot, depth,
                                  screen_space, x, y, rotation_degrees, scale_x,
                                  scale_y, opacity, location, AffineTransform{},
                                  Point{}, 0.0F, 1.0F});
      ++layer_index;
    }

    std::map<std::string, std::uint8_t, std::less<>> visit_state;
    const std::function<std::optional<Error>(const std::string &)>
        resolve_node = [&](const std::string &id) -> std::optional<Error> {
      auto &state = visit_state[id];
      if (state == 2U) {
        return std::nullopt;
      }
      auto &layer = available.at(id);
      if (state == 1U) {
        return document_error("Layer parent graph contains a cycle", pack_file,
                              layer.location + ".parent");
      }
      state = 1U;

      AffineTransform parent_transform;
      float parent_depth = 0.0F;
      float parent_opacity = 1.0F;
      if (layer.parent) {
        if (!available.contains(*layer.parent)) {
          return document_error("Unknown layer parent: " + *layer.parent,
                                pack_file, layer.location + ".parent");
        }
        if (auto error = resolve_node(*layer.parent)) {
          return error;
        }
        const auto &resolved_parent = available.at(*layer.parent);
        parent_transform = resolved_parent.world_transform;
        parent_depth = resolved_parent.world_depth;
        parent_opacity = resolved_parent.world_opacity;
      }

      const auto pivot_point = layer.pivot ? pivots.at(*layer.pivot) : Point{};
      layer.world_transform =
          multiply(parent_transform, local_transform(layer, pivot_point));
      layer.world_pivot = transform_point(layer.world_transform, pivot_point);
      layer.world_depth = parent_depth + layer.depth;
      layer.world_opacity = parent_opacity * layer.opacity;
      state = 2U;
      return std::nullopt;
    };

    for (const auto &[id, layer] : available) {
      static_cast<void>(layer);
      if (auto error = resolve_node(id)) {
        return Result<Scene>::failure(std::move(*error));
      }
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
                if (left.screen_space != right.screen_space) {
                  return !left.screen_space;
                }
                if (left.world_depth != right.world_depth) {
                  return left.world_depth < right.world_depth;
                }
                return left.z < right.z;
              });
    scene.layers.reserve(selected.size());
    for (auto &layer : selected) {
      std::vector<SceneAnimationNode> animation_chain;
      const Layer *node = &layer;
      while (node != nullptr) {
        animation_chain.push_back(
            SceneAnimationNode{node->id, node->world_pivot});
        node = node->parent ? &available.at(*node->parent) : nullptr;
      }
      std::reverse(animation_chain.begin(), animation_chain.end());
      scene.layers.push_back(
          SceneLayer{layer.id, std::move(layer.source),
                     std::move(layer.lod_sources), layer.world_transform,
                     std::move(animation_chain), layer.world_opacity,
                     layer.world_depth, layer.screen_space, layer.z});
      if (layer.collision_bounds) {
        auto visual_transform = layer.world_transform;
        if (!layer.screen_space) {
          visual_transform.translate_x -=
              scene.view_offset_x * layer.world_depth;
          visual_transform.translate_y -=
              scene.view_offset_y * layer.world_depth;
          visual_transform =
              multiply(scene.camera_transform, visual_transform);
        }
        const auto bounds =
            transform_rect(*layer.collision_bounds, visual_transform);
        const auto left = std::max(0.0F, bounds.x - text_clearance);
        const auto top = std::max(0.0F, bounds.y - text_clearance);
        const auto right = std::min(static_cast<float>(scene.width),
                                    bounds.x + bounds.width + text_clearance);
        const auto bottom = std::min(static_cast<float>(scene.height),
                                     bounds.y + bounds.height + text_clearance);
        if (right > left && bottom > top) {
          avoid_regions.push_back(Rect{left, top, right - left, bottom - top});
        }
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
      if (configured.contains("overlays")) {
        const auto &configured_overlays = configured.at("overlays");
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
      }
      if (text_pop && scene.text.empty()) {
        return Result<Scene>::failure(
            document_error("text_pop requires sticker text", sticker_file,
                           "$.animation.overlays"));
      }

      const auto parse_property =
          [](std::string_view name) -> std::optional<AnimationProperty> {
        if (name == "translate_x") {
          return AnimationProperty::translate_x;
        }
        if (name == "translate_y") {
          return AnimationProperty::translate_y;
        }
        if (name == "scale_x") {
          return AnimationProperty::scale_x;
        }
        if (name == "scale_y") {
          return AnimationProperty::scale_y;
        }
        if (name == "rotation_degrees") {
          return AnimationProperty::rotation_degrees;
        }
        if (name == "opacity") {
          return AnimationProperty::opacity;
        }
        if (name == "view_x") {
          return AnimationProperty::view_x;
        }
        if (name == "view_y") {
          return AnimationProperty::view_y;
        }
        return std::nullopt;
      };
      const auto parse_easing =
          [](std::string_view name) -> std::optional<AnimationEasing> {
        if (name == "linear") {
          return AnimationEasing::linear;
        }
        if (name == "ease_out") {
          return AnimationEasing::ease_out;
        }
        if (name == "ease_in_out") {
          return AnimationEasing::ease_in_out;
        }
        if (name == "back_out") {
          return AnimationEasing::back_out;
        }
        return std::nullopt;
      };

      std::vector<AnimationTrack> tracks;
      std::set<std::pair<std::string, std::string>> track_ids;
      if (configured.contains("tracks")) {
        std::size_t track_index = 0;
        for (const auto &configured_track : configured.at("tracks")) {
          const auto track_location =
              "$.animation.tracks[" + std::to_string(track_index) + "]";
          const auto target = configured_track.at("target").get<std::string>();
          const auto property_name =
              configured_track.at("property").get<std::string>();
          const auto property = parse_property(property_name);
          if (!property) {
            return Result<Scene>::failure(document_error(
                "Unknown animation track property: " + property_name,
                sticker_file, track_location + ".property"));
          }
          const auto view_property = *property == AnimationProperty::view_x ||
                                     *property == AnimationProperty::view_y;
          if ((target == "$view") != view_property) {
            return Result<Scene>::failure(document_error(
                "View tracks must target $view and node tracks must target a "
                "selected layer",
                sticker_file, track_location + ".target"));
          }
          if (target != "$view" && !selected_ids.contains(target)) {
            return Result<Scene>::failure(
                document_error("Unknown animation track target: " + target,
                               sticker_file, track_location + ".target"));
          }
          if (!track_ids.emplace(target, property_name).second) {
            return Result<Scene>::failure(document_error(
                "Animation target/property tracks must be unique", sticker_file,
                track_location));
          }

          std::vector<AnimationKeyframe> keyframes;
          std::uint32_t previous_at = 0U;
          std::size_t keyframe_index = 0;
          for (const auto &configured_keyframe :
               configured_track.at("keyframes")) {
            const auto keyframe_location = track_location + ".keyframes[" +
                                           std::to_string(keyframe_index) + "]";
            const auto at_ms =
                configured_keyframe.at("at_ms").get<std::uint32_t>();
            const auto value = configured_keyframe.at("value").get<float>();
            const auto easing_name =
                configured_keyframe.value("easing", std::string{"linear"});
            const auto easing = parse_easing(easing_name);
            if (!easing) {
              return Result<Scene>::failure(
                  document_error("Unknown animation easing: " + easing_name,
                                 sticker_file, keyframe_location + ".easing"));
            }
            if (at_ms > duration_ms ||
                (keyframe_index > 0U && at_ms <= previous_at)) {
              return Result<Scene>::failure(document_error(
                  "Animation keyframe times must be strictly increasing and "
                  "inside the duration",
                  sticker_file, keyframe_location + ".at_ms"));
            }
            const auto valid_value = [&] {
              if (!std::isfinite(value)) {
                return false;
              }
              switch (*property) {
              case AnimationProperty::translate_x:
              case AnimationProperty::translate_y:
                return std::abs(value) <= 4096.0F;
              case AnimationProperty::scale_x:
              case AnimationProperty::scale_y:
                return value >= 0.01F && value <= 100.0F;
              case AnimationProperty::rotation_degrees:
                return std::abs(value) <= 3600.0F;
              case AnimationProperty::opacity:
                return value >= 0.0F && value <= 1.0F;
              case AnimationProperty::view_x:
              case AnimationProperty::view_y:
                return std::abs(value) <= 128.0F;
              }
              return false;
            }();
            if (!valid_value) {
              return Result<Scene>::failure(document_error(
                  "Animation keyframe value is outside property bounds",
                  sticker_file, keyframe_location + ".value"));
            }
            keyframes.push_back(AnimationKeyframe{at_ms, value, *easing});
            previous_at = at_ms;
            ++keyframe_index;
          }
          if (keyframes.size() < 2U || keyframes.front().at_ms != 0U ||
              keyframes.back().at_ms != duration_ms) {
            return Result<Scene>::failure(document_error(
                "Animation tracks require at least two keyframes spanning 0 "
                "through duration_ms",
                sticker_file, track_location + ".keyframes"));
          }
          if (loop == AnimationLoop::loop &&
              keyframes.front().value != keyframes.back().value) {
            return Result<Scene>::failure(document_error(
                "Looping animation tracks must end at their starting value",
                sticker_file, track_location + ".keyframes"));
          }
          tracks.push_back(
              AnimationTrack{target, *property, std::move(keyframes)});
          ++track_index;
        }
      }
      if (overlays.empty() && tracks.empty()) {
        return Result<Scene>::failure(document_error(
            "Animation requires at least one overlay or typed track",
            sticker_file, "$.animation"));
      }
      scene.animation = AnimationSpec{duration_ms, fps,      loop,
                                      body_bounce, text_pop, std::move(tracks)};
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
