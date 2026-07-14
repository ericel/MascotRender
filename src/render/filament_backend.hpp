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
};

// Loads a GLB through Filament's gltfio implementation, validates required
// semantic node names, and returns backend-neutral metadata. The Filament
// objects are intentionally private to the implementation.
[[nodiscard]] Result<GlbAssetInfo>
inspect_filament_glb(const std::filesystem::path &path,
                     const std::vector<std::string> &required_anchors);

} // namespace mascotrender::detail
