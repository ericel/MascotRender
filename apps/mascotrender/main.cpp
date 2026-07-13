#include <CLI/CLI.hpp>
#include <cstddef>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <mascotrender/mascotrender.hpp>
#include <string>

namespace {

int write_image(const mascotrender::Result<mascotrender::EncodedImage>& result,
                const std::string& output_path) {
    if (!result) {
        std::cerr << "render failed: " << result.error().message << '\n';
        if (!result.error().source.empty()) {
            std::cerr << "  source: " << result.error().source;
            if (!result.error().location.empty()) {
                std::cerr << ':' << result.error().location;
            }
            std::cerr << '\n';
        }
        return 1;
    }

    const auto& image = result.value();
    std::ofstream output{output_path, std::ios::binary};
    if (!output) {
        std::cerr << "could not open output: " << output_path << '\n';
        return 1;
    }
    output.write(reinterpret_cast<const char*>(image.bytes.data()),
                 static_cast<std::streamsize>(image.bytes.size()));
    if (!output) {
        std::cerr << "could not write output: " << output_path << '\n';
        return 1;
    }
    std::cout << "wrote " << image.width << 'x' << image.height << " WebP to "
              << output_path << '\n';
    return 0;
}

void add_render_options(CLI::App& command,
                        mascotrender::RenderOptions& options) {
    command.add_option("--width", options.width, "Output width in pixels");
    command.add_option("--height", options.height, "Output height in pixels");
    command.add_option("--quality", options.webp_quality,
                       "WebP quality (0-100)");
    command.add_flag("--lossless", options.lossless,
                     "Use lossless WebP encoding");
    command.add_flag("--first-frame-only", options.animation_first_frame_only,
                     "Render an animation's stable poster frame only");
}

}  // namespace

int main(int argc, char** argv) {
    CLI::App app{"Build-time mascot and sticker rendering engine"};
    app.set_version_flag("--version", mascotrender::version_string());

    std::string output_path;
    mascotrender::RenderOptions options;
    auto* render = app.add_subcommand(
        "render-sample", "Render the deterministic M1 mascot sample to WebP");
    render->add_option("-o,--output", output_path, "Output WebP path")
        ->required();
    add_render_options(*render, options);

    std::string pack_path;
    std::string sticker_path;
    std::string pack_output_path;
    mascotrender::RenderOptions pack_options;
    auto* render_pack = app.add_subcommand(
        "render",
        "Render a versioned mascot pack and sticker JSON specification");
    render_pack->add_option("--pack", pack_path, "Path to pack.json")
        ->required();
    render_pack->add_option("--sticker", sticker_path, "Path to sticker JSON")
        ->required();
    render_pack->add_option("-o,--output", pack_output_path, "Output WebP path")
        ->required();
    add_render_options(*render_pack, pack_options);

    std::string validate_pack_path;
    std::string validate_sticker_path;
    auto* validate = app.add_subcommand(
        "validate",
        "Validate and render-check a pack and sticker specification");
    validate->add_option("--pack", validate_pack_path, "Path to pack.json")
        ->required();
    validate
        ->add_option("--sticker", validate_sticker_path, "Path to sticker JSON")
        ->required();

    CLI11_PARSE(app, argc, argv);

    if (*render) {
        mascotrender::Engine engine;
        return write_image(engine.render_sample(options), output_path);
    }

    if (*render_pack) {
        mascotrender::Engine engine;
        const mascotrender::RenderRequest request{pack_path, sticker_path,
                                                  pack_options};
        return write_image(engine.render(request), pack_output_path);
    }

    if (*validate) {
        mascotrender::Engine engine;
        const mascotrender::RenderRequest request{
            validate_pack_path, validate_sticker_path, {}};
        const auto result = engine.render(request);
        if (!result) {
            std::cerr << "validation failed: " << result.error().message
                      << '\n';
            if (!result.error().source.empty()) {
                std::cerr << "  source: " << result.error().source;
                if (!result.error().location.empty()) {
                    std::cerr << ':' << result.error().location;
                }
                std::cerr << '\n';
            }
            return 1;
        }
        std::cout << "valid: " << result.value().width << 'x'
                  << result.value().height << ", "
                  << result.value().bytes.size() << " encoded bytes\n";
        return 0;
    }

    std::cout << app.help();
    return 0;
}
