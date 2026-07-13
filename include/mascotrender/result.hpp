#pragma once

#include <stdexcept>
#include <utility>
#include <variant>

#include <mascotrender/error.hpp>

namespace mascotrender {

template <typename T>
class Result {
public:
    [[nodiscard]] static Result success(T value) {
        return Result{std::move(value)};
    }

    [[nodiscard]] static Result failure(Error error) {
        return Result{std::move(error)};
    }

    [[nodiscard]] bool has_value() const noexcept {
        return std::holds_alternative<T>(storage_);
    }

    [[nodiscard]] explicit operator bool() const noexcept { return has_value(); }

    [[nodiscard]] T& value() & {
        if (!has_value()) {
            throw std::logic_error{"MascotRender Result does not contain a value"};
        }
        return std::get<T>(storage_);
    }

    [[nodiscard]] const T& value() const& {
        if (!has_value()) {
            throw std::logic_error{"MascotRender Result does not contain a value"};
        }
        return std::get<T>(storage_);
    }

    [[nodiscard]] T&& value() && {
        if (!has_value()) {
            throw std::logic_error{"MascotRender Result does not contain a value"};
        }
        return std::get<T>(std::move(storage_));
    }

    [[nodiscard]] Error& error() & {
        if (has_value()) {
            throw std::logic_error{"MascotRender Result does not contain an error"};
        }
        return std::get<Error>(storage_);
    }

    [[nodiscard]] const Error& error() const& {
        if (has_value()) {
            throw std::logic_error{"MascotRender Result does not contain an error"};
        }
        return std::get<Error>(storage_);
    }

private:
    explicit Result(T value) : storage_{std::move(value)} {}
    explicit Result(Error error) : storage_{std::move(error)} {}

    std::variant<T, Error> storage_;
};

}  // namespace mascotrender
