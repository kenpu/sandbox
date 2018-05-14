create table users (
    id varchar(255) primary key,
    name varchar(255),
    email varchar(255)
);

--;;

create table activities (
    user_id varchar(255),
    activity varchar(255),
    foreign key (user_id) references users (id) on delete cascade
);
