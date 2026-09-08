#!/bin/bash
set -e
cd ~ || exit

echo "::group::Install Bench"
pip install frappe-bench
echo "::endgroup::"

echo "::group::Init Bench"
FRAPPE_URL=https://github.com/kehwar/frappe.git
FRAPPE_REVISION=853bb604f079c79d628ba617f9d4b3b502b0a626
FRAPPE_SOURCE_ROOT=$(mktemp -d)
FRAPPE_SOURCE="$FRAPPE_SOURCE_ROOT/frappe"
git init --initial-branch nubefact-pinned "$FRAPPE_SOURCE"
git -C "$FRAPPE_SOURCE" remote add origin "$FRAPPE_URL"
git -C "$FRAPPE_SOURCE" fetch --depth 1 origin "$FRAPPE_REVISION"
git -C "$FRAPPE_SOURCE" checkout -B nubefact-pinned "$FRAPPE_REVISION"
bench -v init frappe-bench --skip-assets --python "$(which python)" --frappe-path "$FRAPPE_SOURCE" --frappe-branch nubefact-pinned
git -C frappe-bench/apps/frappe remote set-url upstream "$FRAPPE_URL"
git -C frappe-bench/apps/frappe checkout --detach --force "$FRAPPE_REVISION"
rm -rf "$FRAPPE_SOURCE_ROOT"
test "$(git -C frappe-bench/apps/frappe rev-parse HEAD)" = "$FRAPPE_REVISION"
cd ./frappe-bench || exit

bench get-app --skip-assets --branch v15.103.1 https://github.com/frappe/erpnext.git
test "$(git -C apps/erpnext rev-parse HEAD)" = "2597eaad5195ea4a3c89e0c2fae29e62451b742c"
bench -v setup requirements --dev
if [ "$TYPE" == "ui" ]
then
  bench -v setup requirements --node;
fi
echo "::endgroup::"

echo "::group::Get Nubefact App"
bench get-app "${GITHUB_WORKSPACE}"
echo "::endgroup::"

echo "::group::Create Test Site"
mkdir ~/frappe-bench/sites/test_site
cp "${GITHUB_WORKSPACE}/.github/helper/db/$DB.json" ~/frappe-bench/sites/test_site/site_config.json

if [ "$DB" == "mariadb" ]
then
  export MYSQL_PWD=travis
  mariadb --host 127.0.0.1 --port 3306 -u root -e "SET GLOBAL character_set_server = 'utf8mb4'";
  mariadb --host 127.0.0.1 --port 3306 -u root -e "SET GLOBAL collation_server = 'utf8mb4_unicode_ci'";

  mariadb --host 127.0.0.1 --port 3306 -u root -e "CREATE DATABASE test_frappe";
  mariadb --host 127.0.0.1 --port 3306 -u root -e "CREATE USER 'test_frappe'@'%' IDENTIFIED BY 'test_frappe'";
  mariadb --host 127.0.0.1 --port 3306 -u root -e "GRANT ALL PRIVILEGES ON \`test_frappe\`.* TO 'test_frappe'@'%'";
  mariadb --host 127.0.0.1 --port 3306 -u root -e "FLUSH PRIVILEGES";
  unset MYSQL_PWD
fi

if [ "$DB" == "postgres" ]
then
  export PGPASSWORD=travis
  psql -h 127.0.0.1 -p 5432 -c "CREATE DATABASE test_frappe" -U postgres;
  psql -h 127.0.0.1 -p 5432 -c "CREATE USER test_frappe WITH PASSWORD 'test_frappe'" -U postgres;
  unset PGPASSWORD
fi
echo "::endgroup::"

echo "::group::Modify processes"
sed -i 's/^watch:/# watch:/g' Procfile
sed -i 's/^schedule:/# schedule:/g' Procfile

if [ "$TYPE" == "server" ]
then
  sed -i 's/^socketio:/# socketio:/g' Procfile
  sed -i 's/^redis_socketio:/# redis_socketio:/g' Procfile
fi

if [ "$TYPE" == "ui" ]
then
  sed -i 's/^web: bench serve/web: bench serve --with-coverage/g' Procfile
fi
echo "::endgroup::"

bench start &> ~/frappe-bench/bench_start.log &

echo "::group::Install site"
if [ "$TYPE" == "server" ]
then
  CI=Yes bench build --app frappe &
  build_pid=$!
fi

bench --site test_site reinstall --yes
bench --site test_site install-app erpnext
bench --site test_site install-app nubefact

if [ "$TYPE" == "server" ]
then
  wait $build_pid
fi
echo "::endgroup::"
