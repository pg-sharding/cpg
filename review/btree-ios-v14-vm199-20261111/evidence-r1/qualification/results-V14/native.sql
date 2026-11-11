CREATE OR REPLACE FUNCTION ios_dispatch_oracle() RETURNS bigint AS '/home/reshke/wpgpg/ios14-199-1111/qualification/micro-V14/ios_dispatch.so', 'ios_dispatch_oracle' LANGUAGE C STRICT;
CREATE OR REPLACE FUNCTION ios_pagecache_oracle() RETURNS bigint AS '/home/reshke/wpgpg/ios14-199-1111/qualification/micro-V14/ios_dispatch.so', 'ios_pagecache_oracle' LANGUAGE C STRICT;
CREATE OR REPLACE FUNCTION ios_slot_micro(integer,bigint,integer,boolean,boolean,boolean) RETURNS bigint AS '/home/reshke/wpgpg/ios14-199-1111/qualification/micro-V14/ios_slot.so', 'ios_slot_micro' LANGUAGE C STRICT;
SELECT 'oracle',ios_dispatch_oracle();
SELECT 'contract',ios_pagecache_oracle();
SELECT 'slot2r2',ios_slot_micro(2,128,2,true,false,false);
SELECT 'slot2r64',ios_slot_micro(2,128,64,true,false,false);
SELECT 'slot8',ios_slot_micro(8,128,64,true,true,false);
SELECT 'slot32null',ios_slot_micro(32,128,64,true,true,true);
