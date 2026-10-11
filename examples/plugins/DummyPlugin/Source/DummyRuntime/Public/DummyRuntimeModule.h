// uebuild example module header.
#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"

class FDummyRuntimeModule : public IModuleInterface
{
public:
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;
};
