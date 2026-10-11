// uebuild example editor-only module (skipped for non-editor targets).
#include "Modules/ModuleManager.h"

class FDummyEditorModule : public IModuleInterface
{
};

IMPLEMENT_MODULE(FDummyEditorModule, DummyEditor)
