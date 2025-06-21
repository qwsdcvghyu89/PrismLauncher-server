#pragma once
#include <QCommandLineParser>
#include <QCoreApplication>
#include <QNetworkAccessManager>

class ModpackCLI {
   public:
    ModpackCLI(QCoreApplication& app);
    bool run();

   private:
    bool search(const QString& name);
    bool download(const QString& idOrUrl, const QString& dest);
    static QString extractId(const QString& input);

    QCoreApplication& m_app;
    QNetworkAccessManager m_manager;
    QCommandLineParser m_parser;
};
