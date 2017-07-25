#!/usr/local/bin/perl
use XML::LibXSLT;
use XML::LibXML;

if( defined($ARGV[0]) && ($ARGV[0] =~ '/^id=([A-z0-9]+.*)/') ) {
  my ${ID} = $1;
}
my $parser = XML::LibXML->new();
my $xslt = XML::LibXSLT->new();
my $source = $parser->parse_file('../../sitemap.xml');
my $style_doc = $parser->parse_file('jcdsee.xsl');

my $stylesheet = $xslt->parse_stylesheet($style_doc);

my $results = $stylesheet->transform($source);
print "Content-type: text/html\n\n";

print $stylesheet->output_string($results);

