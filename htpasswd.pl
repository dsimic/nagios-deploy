#!/usr/bin/perl
 
use strict;
 
if ( @ARGV != 2 ){
    print "usage: /usr/local/bin/htpasswd.pl <username> <password>\n";
}
else {
    print $ARGV[0].":".crypt($ARGV[1],$ARGV[1])."\n";
}
