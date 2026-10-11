// uebuild example module implementation.
#include "DummyRuntimeModule.h"

#define LOCTEXT_NAMESPACE "FDummyRuntimeModule"

void FDummyRuntimeModule::StartupModule()
{
}

void FDummyRuntimeModule::ShutdownModule()
{
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FDummyRuntimeModule, DummyRuntime)
