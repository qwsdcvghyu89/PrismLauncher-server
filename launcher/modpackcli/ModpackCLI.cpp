#include "ModpackCLI.h"
#include "buildconfig/BuildConfig.h"

#include <QDir>
#include <QEventLoop>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QUrl>
#include <QUrlQuery>
#include <iostream>

namespace {
// RAII helper for finally semantics
template <typename F>
struct FinalAction {
    F f;
    ~FinalAction() { f(); }
};
}  // namespace

ModpackCLI::ModpackCLI(QCoreApplication& app) : m_app(app)
{
    m_parser.setApplicationDescription("Modpack command line interface");
    m_parser.addHelpOption();
    m_parser.addVersionOption();
    m_parser.addOptions({ { { "s", "search" }, "Search modpacks by name", "name" },
                          { { "d", "download" }, "Download modpack by id or url", "id" },
                          { "dest", "Destination directory", "path" } });
    m_parser.process(m_app);
}

bool ModpackCLI::run()
{
    if (m_parser.isSet("search")) {
        return search(m_parser.value("search"));
    } else if (m_parser.isSet("download")) {
        return download(m_parser.value("download"), m_parser.value("dest"));
    }
    m_parser.showHelp();
    return false;
}

static bool waitForFinished(QNetworkReply* reply)
{
    QEventLoop loop;
    QObject::connect(reply, &QNetworkReply::finished, &loop, &QEventLoop::quit);
    loop.exec();
    return reply->error() == QNetworkReply::NoError;
}

bool ModpackCLI::search(const QString& name)
{
    try {
        QString url = BuildConfig.MODRINTH_PROD_URL + "/search?query=" + QUrl::toPercentEncoding(name) +
                      "&limit=10&facets=[[\"project_type:modpack\"]]";
        QNetworkReply* reply = m_manager.get(QNetworkRequest(QUrl(url)));
        FinalAction cleanup{ [reply]() { reply->deleteLater(); } };
        if (!waitForFinished(reply))
            throw std::runtime_error(reply->errorString().toStdString());

        QJsonDocument doc = QJsonDocument::fromJson(reply->readAll());
        auto hits = doc.object().value("hits").toArray();
        for (const QJsonValue& v : hits) {
            auto obj = v.toObject();
            std::cout << obj.value("title").toString().toStdString() << " (" << obj.value("project_id").toString().toStdString() << ")\n";
        }
        return true;
    } catch (std::exception& e) {
        std::cerr << "Search failed: " << e.what() << std::endl;
        return false;
    }
}

QString ModpackCLI::extractId(const QString& input)
{
    if (input.startsWith("http")) {
        QUrl url(input);
        auto parts = url.path().split('/', Qt::SkipEmptyParts);
        if (parts.size() >= 2)
            return parts.at(1);
    }
    return input;
}

bool ModpackCLI::download(const QString& idOrUrl, const QString& dest)
{
    try {
        QString id = extractId(idOrUrl);
        if (id.isEmpty())
            throw std::runtime_error("Invalid modpack identifier");

        QUrl versionsUrl(QString("%1/project/%2/version").arg(BuildConfig.MODRINTH_PROD_URL, id));
        QNetworkReply* verReply = m_manager.get(QNetworkRequest(versionsUrl));
        FinalAction cleanupVer{ [verReply]() { verReply->deleteLater(); } };
        if (!waitForFinished(verReply))
            throw std::runtime_error(verReply->errorString().toStdString());

        QJsonDocument doc = QJsonDocument::fromJson(verReply->readAll());
        if (!doc.isArray() || doc.array().isEmpty())
            throw std::runtime_error("No versions found for modpack");
        QJsonObject verObj = doc.array().first().toObject();
        QJsonArray files = verObj.value("files").toArray();
        if (files.isEmpty())
            throw std::runtime_error("No files available for modpack");

        QJsonObject fileObj = files.first().toObject();
        QString fileUrl = fileObj.value("url").toString();
        QString fileName = fileObj.value("filename").toString();
        QString target = dest.isEmpty() ? QDir::current().filePath(fileName) : QDir(dest).filePath(fileName);

        QNetworkReply* dl = m_manager.get(QNetworkRequest(QUrl(fileUrl)));
        QFile out(target);
        if (!out.open(QIODevice::WriteOnly))
            throw std::runtime_error(QString("Cannot open %1").arg(target).toStdString());
        FinalAction cleanupFile{ [&out]() { out.close(); } };
        FinalAction cleanupDl{ [dl]() { dl->deleteLater(); } };
        QObject::connect(dl, &QNetworkReply::readyRead, [&]() { out.write(dl->readAll()); });
        if (!waitForFinished(dl)) {
            out.remove();
            throw std::runtime_error(dl->errorString().toStdString());
        }
        out.write(dl->readAll());
        std::cout << "Downloaded to " << target.toStdString() << std::endl;
        return true;
    } catch (std::exception& e) {
        std::cerr << "Download failed: " << e.what() << std::endl;
        return false;
    }
}
