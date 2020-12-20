create table if not exists remote_movies (
    id integer primary key autoincrement,
    guid text not null,
    remote_path text not null,
    queued integer default 0,
    complete integer default 0
);
