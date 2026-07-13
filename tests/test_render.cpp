#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <vector>

#include <catch2/catch_test_macros.hpp>
#include <webp/decode.h>

#include <mascotrender/mascotrender.hpp>

namespace {

[[nodiscard]] std::uint8_t byte_at(
    const std::vector<std::byte>& bytes, std::size_t index) {
    return std::to_integer<std::uint8_t>(bytes.at(index));
}

}  // namespace

TEST_CASE("sample render is a deterministic transparent WebP") {
    mascotrender::Engine engine;

    auto first = engine.render_sample();
    REQUIRE(first);
    auto second = engine.render_sample();
    REQUIRE(second);

    const auto& image = first.value();
    REQUIRE(image.width == 512);
    REQUIRE(image.height == 512);
    REQUIRE(image.media_type == "image/webp");
    REQUIRE(image.bytes.size() > 12);
    REQUIRE(byte_at(image.bytes, 0) == 'R');
    REQUIRE(byte_at(image.bytes, 1) == 'I');
    REQUIRE(byte_at(image.bytes, 2) == 'F');
    REQUIRE(byte_at(image.bytes, 3) == 'F');
    REQUIRE(byte_at(image.bytes, 8) == 'W');
    REQUIRE(byte_at(image.bytes, 9) == 'E');
    REQUIRE(byte_at(image.bytes, 10) == 'B');
    REQUIRE(byte_at(image.bytes, 11) == 'P');
    REQUIRE(image.bytes == second.value().bytes);

    WebPBitstreamFeatures features{};
    const auto* encoded =
        reinterpret_cast<const std::uint8_t*>(image.bytes.data());
    REQUIRE(WebPGetFeatures(encoded, image.bytes.size(), &features) == VP8_STATUS_OK);
    REQUIRE(features.width == 512);
    REQUIRE(features.height == 512);
    REQUIRE(features.has_alpha == 1);

    std::vector<std::uint8_t> decoded(512U * 512U * 4U);
    REQUIRE(WebPDecodeBGRAInto(encoded, image.bytes.size(), decoded.data(),
                               decoded.size(), 512 * 4) != nullptr);

    bool found_transparent = false;
    bool found_opaque = false;
    for (std::size_t offset = 3; offset < decoded.size(); offset += 4) {
        found_transparent = found_transparent || decoded[offset] == 0;
        found_opaque = found_opaque || decoded[offset] == 255;
    }
    REQUIRE(found_transparent);
    REQUIRE(found_opaque);
}

TEST_CASE("render options are validated at the public boundary") {
    mascotrender::Engine engine;
    mascotrender::RenderOptions options;

    options.width = 0;
    auto dimensions = engine.render_sample(options);
    REQUIRE_FALSE(dimensions);
    REQUIRE(dimensions.error().code == mascotrender::ErrorCode::invalid_argument);

    options.width = 512;
    options.webp_quality = 101.0F;
    auto quality = engine.render_sample(options);
    REQUIRE_FALSE(quality);
    REQUIRE(quality.error().code == mascotrender::ErrorCode::invalid_argument);

    options.webp_quality = std::numeric_limits<float>::quiet_NaN();
    auto not_a_number = engine.render_sample(options);
    REQUIRE_FALSE(not_a_number);
    REQUIRE(not_a_number.error().code == mascotrender::ErrorCode::invalid_argument);
}
