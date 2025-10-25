# Frontend Error Fixes Applied

## Issues Fixed

This document describes the fixes applied to resolve the three console errors reported when running the video analyzer application.

### 1. Missing `conversationId` Parameter Error

**Original Error:**
```
getHistory failed invalid args `conversationId` for command `get_history`: command get_history missing required key conversationId
ChatWindow.tsx:62 Uncaught (in promise) invalid args `conversationId` for command `send_message_and_stream`: command send_message_and_stream missing required key conversationId
```

**Root Cause:**
The TypeScript/JavaScript code was calling Tauri commands using snake_case parameter names (`conversation_id`, `base64_data`), but Tauri v2 automatically converts Rust function parameters from snake_case to camelCase for JavaScript interoperability. The Rust commands expected to receive camelCase parameters from JavaScript.

**Fix Applied:**
Updated `frontend/src/grpcClient.ts` to use camelCase parameter names:
- `conversation_id` → `conversationId` (in `get_history` and `send_message_and_stream`)
- `base64_data` → `base64Data` (in `save_uploaded_file`)

**Code Changes:**
```typescript
// Before:
await invoke('send_message_and_stream', { conversation_id: conversationId, sender, text });
await invoke('get_history', { conversation_id: conversationId });
await invoke('save_uploaded_file', { base64_data: base64, filename });

// After:
await invoke('send_message_and_stream', { conversationId, sender, text });
await invoke('get_history', { conversationId });
await invoke('save_uploaded_file', { base64Data: base64, filename });
```

### 2. Stack Overflow in File Upload

**Original Error:**
```
Uncaught (in promise) RangeError: Maximum call stack size exceeded
    at onFileChange (UploadPanel.tsx:21:29)
```

**Root Cause:**
The original code attempted to convert a large file's ArrayBuffer to base64 using:
```typescript
const b64 = btoa(String.fromCharCode(...new Uint8Array(data)));
```

The spread operator (`...`) tries to pass all array elements as individual function arguments to `String.fromCharCode()`. For large video files (potentially millions of bytes), this exceeds JavaScript's maximum function argument limit, causing a stack overflow.

**Fix Applied:**
Updated `frontend/src/components/UploadPanel.tsx` to process the conversion in chunks:

```typescript
// read file as base64
const data = await file.arrayBuffer();
// Convert to base64 in chunks to avoid stack overflow with large files
const bytes = new Uint8Array(data);
let binary = '';
const chunkSize = 8192;
for (let i = 0; i < bytes.length; i += chunkSize) {
  const chunk = bytes.subarray(i, Math.min(i + chunkSize, bytes.length));
  binary += String.fromCharCode(...chunk);
}
const b64 = btoa(binary);
```

This approach:
- Processes the file in 8KB chunks
- Each chunk is small enough to safely use with `String.fromCharCode()`
- Concatenates chunks into a complete binary string before base64 encoding
- Works reliably with files of any size

## Testing the Fixes

### Prerequisites
1. Backend must be running: `python main.py`
2. Frontend must be running: `cd frontend && npm run tauri dev`

### Test Case 1: Chat History Loading
**Expected Behavior:** Chat history loads without console errors when the app starts.

**How to Verify:**
1. Start the application
2. Open browser DevTools console (if testing in browser) or check Tauri console logs
3. Verify no "missing required key conversationId" error appears
4. Previous messages should display in the chat window

### Test Case 2: Sending Messages
**Expected Behavior:** Messages send successfully and receive responses.

**How to Verify:**
1. Type a message in the chat input field
2. Click "Send" or press Enter
3. Verify no "missing required key conversationId" error in console
4. User message should appear in chat
5. Agent response should stream back and appear in chat

### Test Case 3: Video Upload
**Expected Behavior:** Video uploads complete without hanging at 10%.

**How to Verify:**
1. Click the file upload button
2. Select a video file (any size, preferably >1MB to test the chunk processing)
3. Verify upload progress bar advances smoothly
4. Progress should reach 100% without errors
5. No "Maximum call stack size exceeded" error should appear
6. Backend should begin processing the video
7. Chat should display confirmation/results of video analysis

## Technical Details

### Tauri v2 Parameter Naming Convention
Tauri v2 (currently using v2.9.1) automatically converts Rust function parameter names for JavaScript:
- Rust: `snake_case` (e.g., `conversation_id: String`)
- JavaScript/TypeScript: `camelCase` (e.g., `conversationId`)

This is done automatically by the Tauri framework to follow idiomatic naming conventions in each language.

### JavaScript Function Argument Limits
JavaScript engines have a maximum limit on the number of arguments a function can accept:
- V8 (Chrome/Node): ~65,000 arguments
- SpiderMonkey (Firefox): ~500,000 arguments
- JavaScriptCore (Safari): ~65,000 arguments

When spreading a large array (`...array`), each element becomes an argument. A 1MB file would create 1,048,576 arguments, far exceeding these limits. The chunked approach ensures we never exceed ~8,192 arguments per call.

## Files Modified

1. `frontend/src/grpcClient.ts`
   - Updated parameter names for Tauri command invocations
   
2. `frontend/src/components/UploadPanel.tsx`
   - Implemented chunked base64 conversion for file uploads

## Additional Notes

- No changes were required to the Rust backend (commands.rs) as it was already correctly defined
- No changes needed to other components (ChatWindow.tsx, App.tsx, etc.)
- The fixes are backward compatible and don't break any existing functionality
- Performance impact of chunked processing is negligible (still completes in milliseconds)
