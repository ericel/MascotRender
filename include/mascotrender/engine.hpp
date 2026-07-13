#pragma once

#include <filesystem>
#include <memory>

#include <mascotrender/export.hpp>
#include <mascotrender/image.hpp>
#include <mascotrender/result.hpp>

namespace mascotrender {

struct RenderRequest {
    // Versioned local pack and sticker documents. Asset paths are resolved
    // relative to the pack and constrained to its canonical directory.
    std::filesystem::path pack_file;
    std::filesystem::path sticker_file;
    RenderOptions options;
};

// Dependency-free public entry point. Engine owns its private renderer state.
class MASCOTRENDER_API Engine final {
public:
    Engine();
    ~Engine();

    Engine(Engine&&) noexcept;
    Engine& operator=(Engine&&) noexcept;

    Engine(const Engine&) = delete;
    Engine& operator=(const Engine&) = delete;

    [[nodiscard]] Result<EncodedImage> render_sample(
        const RenderOptions& options = {}) const;

    // Renders a trusted local pack into an owned in-memory WebP image. All
    // failures are returned as structured values; no exception crosses the API.
    [[nodiscard]] Result<EncodedImage> render(
        const RenderRequest& request) const;

private:
    class Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace mascotrender
