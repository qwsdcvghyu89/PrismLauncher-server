#include <QCoreApplication>
#include "ModpackCLI.h"

int main(int argc, char* argv[])
{
    QCoreApplication app(argc, argv);
    ModpackCLI cli(app);
    bool ok = cli.run();
    return ok ? 0 : 1;
}
