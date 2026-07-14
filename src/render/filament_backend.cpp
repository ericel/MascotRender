#include "render/filament_backend.hpp"

#include <filament/Engine.h>
#include <gltfio/Animator.h>
#include <gltfio/AssetLoader.h>
#include <gltfio/FilamentAsset.h>
#include <gltfio/FilamentInstance.h>
#include <gltfio/MaterialProvider.h>
#include <utils/EntityManager.h>
#include <utils/NameComponentManager.h>

#include <algorithm>
#include <array>
#include <fstream>
#include <iterator>
#include <limits>
#include <memory>
#include <sstream>

namespace mascotrender::detail {
namespace {

constexpr std::size_t max_glb_bytes = 64U * 1024U * 1024U;
constexpr std::array<std::uint8_t, 4> glb_magic{'g', 'l', 'T', 'F'};

struct EngineDeleter {
  void operator()(filament::Engine *engine) const noexcept {
    if (engine != nullptr) {
      filament::Engine::destroy(&engine);
    }
  }
};

struct MaterialProviderDeleter {
  void
  operator()(filament::gltfio::MaterialProvider *materials) const noexcept {
    if (materials != nullptr) {
      materials->destroyMaterials();
      delete materials;
    }
  }
};

struct AssetLoaderDeleter {
  void operator()(filament::gltfio::AssetLoader *loader) const noexcept {
    if (loader != nullptr) {
      filament::gltfio::AssetLoader::destroy(&loader);
    }
  }
};

struct AssetDeleter {
  filament::gltfio::AssetLoader *loader{};

  void operator()(filament::gltfio::FilamentAsset *asset) const noexcept {
    if (asset != nullptr) {
      loader->destroyAsset(asset);
    }
  }
};

[[nodiscard]] Result<std::vector<std::uint8_t>>
read_glb(const std::filesystem::path &path) {
  std::error_code size_error;
  const auto size = std::filesystem::file_size(path, size_error);
  if (size_error) {
    return Result<std::vector<std::uint8_t>>::failure(
        Error{ErrorCode::io_error, "Cannot read GLB file size", path.string()});
  }
  if (size < 12U || size > max_glb_bytes ||
      size > std::numeric_limits<std::uint32_t>::max()) {
    return Result<std::vector<std::uint8_t>>::failure(
        Error{ErrorCode::invalid_document,
              "GLB must be between 12 bytes and the 64 MiB safety limit",
              path.string()});
  }

  std::ifstream input{path, std::ios::binary};
  if (!input) {
    return Result<std::vector<std::uint8_t>>::failure(
        Error{ErrorCode::io_error, "Cannot open GLB file", path.string()});
  }
  std::vector<std::uint8_t> bytes{std::istreambuf_iterator<char>{input},
                                  std::istreambuf_iterator<char>{}};
  if (bytes.size() != size ||
      !std::equal(glb_magic.begin(), glb_magic.end(), bytes.begin())) {
    return Result<std::vector<std::uint8_t>>::failure(
        Error{ErrorCode::invalid_document, "File is not a GLB 2.0 document",
              path.string()});
  }
  if (bytes[4] != 2U || bytes[5] != 0U || bytes[6] != 0U || bytes[7] != 0U) {
    return Result<std::vector<std::uint8_t>>::failure(
        Error{ErrorCode::invalid_document, "Only GLB version 2 is supported",
              path.string()});
  }
  return Result<std::vector<std::uint8_t>>::success(std::move(bytes));
}

} // namespace

Result<GlbAssetInfo>
inspect_filament_glb(const std::filesystem::path &path,
                     const std::vector<std::string> &required_anchors) {
  auto bytes = read_glb(path);
  if (!bytes) {
    return Result<GlbAssetInfo>::failure(bytes.error());
  }

  std::unique_ptr<filament::Engine, EngineDeleter> engine{
      filament::Engine::create()};
  if (!engine) {
    return Result<GlbAssetInfo>::failure(
        Error{ErrorCode::renderer_initialization_failed,
              "Filament could not create a rendering engine", path.string()});
  }

  utils::NameComponentManager names{utils::EntityManager::get()};
  std::unique_ptr<filament::gltfio::MaterialProvider, MaterialProviderDeleter>
      materials{filament::gltfio::createJitShaderProvider(engine.get())};
  if (!materials) {
    return Result<GlbAssetInfo>::failure(Error{
        ErrorCode::renderer_initialization_failed,
        "Filament could not create a glTF material provider", path.string()});
  }

  filament::gltfio::AssetConfiguration configuration{};
  configuration.engine = engine.get();
  configuration.materials = materials.get();
  configuration.names = &names;
  std::unique_ptr<filament::gltfio::AssetLoader, AssetLoaderDeleter> loader{
      filament::gltfio::AssetLoader::create(configuration)};
  if (!loader) {
    return Result<GlbAssetInfo>::failure(
        Error{ErrorCode::renderer_initialization_failed,
              "Filament could not create a GLB loader", path.string()});
  }

  auto *loaded = loader->createAsset(
      bytes.value().data(), static_cast<std::uint32_t>(bytes.value().size()));
  std::unique_ptr<filament::gltfio::FilamentAsset, AssetDeleter> asset{
      loaded, AssetDeleter{loader.get()}};
  if (!asset) {
    return Result<GlbAssetInfo>::failure(
        Error{ErrorCode::invalid_document, "Filament rejected the GLB document",
              path.string()});
  }

  std::vector<std::string> missing;
  for (const auto &anchor : required_anchors) {
    if (anchor.empty() || !asset->getFirstEntityByName(anchor.c_str())) {
      missing.push_back(anchor.empty() ? "<empty>" : anchor);
    }
  }
  if (!missing.empty()) {
    std::ostringstream message;
    message << "GLB is missing required semantic anchor";
    if (missing.size() != 1U) {
      message << 's';
    }
    message << ": ";
    for (std::size_t index = 0; index < missing.size(); ++index) {
      if (index != 0U) {
        message << ", ";
      }
      message << missing[index];
    }
    return Result<GlbAssetInfo>::failure(
        Error{ErrorCode::invalid_document, message.str(), path.string()});
  }

  std::size_t morph_targets = 0U;
  const auto *renderables = asset->getRenderableEntities();
  for (std::size_t index = 0; index < asset->getRenderableEntityCount();
       ++index) {
    morph_targets += asset->getMorphTargetCountAt(renderables[index]);
  }

  std::size_t animations = 0U;
  if (auto *instance = asset->getInstance(); instance != nullptr) {
    if (auto *animator = instance->getAnimator(); animator != nullptr) {
      animations = animator->getAnimationCount();
    }
  }

  return Result<GlbAssetInfo>::success(GlbAssetInfo{
      static_cast<std::uint32_t>(asset->getEntityCount()),
      static_cast<std::uint32_t>(asset->getRenderableEntityCount()),
      static_cast<std::uint32_t>(asset->getCameraEntityCount()),
      static_cast<std::uint32_t>(asset->getLightEntityCount()),
      static_cast<std::uint32_t>(animations),
      static_cast<std::uint32_t>(morph_targets), required_anchors});
}

} // namespace mascotrender::detail
