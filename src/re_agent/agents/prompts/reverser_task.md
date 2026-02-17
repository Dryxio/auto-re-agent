Reverse the following function into clean C++23.

**Target:** ${class_name}::${function_name} at ${address}

**Ghidra Decompile:**
```
${decompiled}
```

**Cross-references (calls from this function):**
${xrefs}

**Struct/type context:**
${structs}

**Existing source context:**
${source_context}

Requirements:
1. Match every branch and call from the decompile
2. Map all offsets (e.g. param_1 + 0x88) to real member names
3. Preserve exact expression/operand order
4. Use existing project patterns and naming conventions
5. Output the complete function implementation in a ```cpp block
6. End with: REVERSED_FUNCTION: ${class_name}::${function_name} (${address})
