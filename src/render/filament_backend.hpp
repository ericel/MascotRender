#pragma once

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <mascotrender/result.hpp>
#include <string>
#include <vector>

namespace mascotrender::detail {

struct GlbAssetInfo {
  std::uint32_t entity_count{};
  std::uint32_t renderable_count{};
  std::uint32_t camera_count{};
  std::uint32_t light_count{};
  std::uint32_t animation_count{};
  std::uint32_t morph_target_count{};
  std::vector<std::string> semantic_anchors;
  std::vector<std::string> animation_names;
  std::vector<float> animation_durations_seconds;
  std::vector<std::string> morph_target_names;
};

struct FilamentRenderOptions {
  std::uint32_t width{256U};
  std::uint32_t height{256U};
  float vertical_span{2.5F};
  std::string animation_name;
  float animation_time_seconds{0.0F};
};

struct FilamentFrame {
  std::uint32_t width{};
  std::uint32_t height{};
  std::vector<std::uint8_t> rgba;
};

// Loads a GLB through Filament's gltfio implementation, validates required
// semantic node names, and returns backend-neutral metadata. The Filament
// objects are intentionally private to the implementation.
[[nodiscard]] Result<GlbAssetInfo>
inspect_filament_glb(const std::filesystem::path &path,
                     const std::vector<std::string> &required_anchors);

// Renders a GLB into owned RGBA pixels using a fixed orthographic camera and
// deterministic hard key light. This remains internal until the common scene
// compiler can select the 3D backend through the public renderer contract.
[[nodiscard]] Result<FilamentFrame>
render_filament_glb(const std::filesystem::path &path,
                    const FilamentRenderOptions &options = {});

} // namespace mascotrender::detail
