#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>

// RAM only; bounded to the most recent acknowledged exchange for each slot.
// Keep the exact reply bytes: re-encrypting a changed reply under the same
// direction/sequence nonce would violate AES-GCM's nonce uniqueness rule.
constexpr uint32_t FG_REPLY_CACHE_TTL_MS = 60000;
struct FgReplyCache {
  uint32_t receivedAt = 0;
  size_t requestLength = 0;
  size_t replyLength = 0;
  bool queued = false;
  uint8_t request[255] = {};
  uint8_t reply[255] = {};
};
bool fgCachedRequestMatches(const FgReplyCache &cached, const uint8_t *frame,
                            size_t length, uint32_t now) {
  return length <= sizeof(cached.request) && length == cached.requestLength &&
    cached.requestLength > 0 && (uint32_t)(now - cached.receivedAt) < FG_REPLY_CACHE_TTL_MS &&
    !memcmp(frame, cached.request, length);
}
void fgRememberRequest(FgReplyCache &cached, const uint8_t *frame, size_t length, uint32_t now) {
  cached.receivedAt = now;
  cached.requestLength = length <= sizeof(cached.request) ? length : 0;
  cached.replyLength = 0;
  cached.queued = false;
  if (cached.requestLength) memcpy(cached.request, frame, length);
}
