# UE 5.8 Build Troubleshooting Guide

## Common Issues & Solutions

### 1. `Engine not found`
**Cause**: Unreal Engine installation directory could not be auto-detected in standard paths.  
**Resolution**:
- Set the environment variable:
  ```bash
  export UNREAL_INSTALL_DIR="/path/to/UnrealEngine"
  ```
- Or pass the explicit engine path to `agentic`:
  ```bash
  agentic build MyPlugin --engine-path "/path/to/UnrealEngine"
  ```

### 2. Missing `.generated.h` include
**Error**: `error: use of undeclared identifier 'GENERATED_BODY'` or compiler failure in UCLASS header.  
**Resolution**:
Ensure `#include "<ClassHeaderName>.generated.h"` is present and is the **very last** `#include` directive before the class declaration.

### 3. Raw pointer vs `TObjectPtr` warnings
**Error/Warning**: `Member variable 'Ptr' has raw pointer type UMyObject*`.  
**Resolution**:
Modern Unreal Engine 5 uses `TObjectPtr<T>` for garbage-collected pointer properties:
```cpp
// Correct:
UPROPERTY(EditAnywhere, BlueprintReadWrite)
TObjectPtr<UStaticMeshComponent> MeshComponent;

// Avoid:
UPROPERTY(EditAnywhere, BlueprintReadWrite)
UStaticMeshComponent* MeshComponent;
```

### 4. UBT Mutex Lock on Windows
**Error**: `UBT: A previous instance of UnrealBuildTool is already running.`  
**Resolution**:
The build runner supplies `-WaitMutex` on Windows. If UBT is hung, terminate `UnrealBuildTool.exe` from Task Manager.
