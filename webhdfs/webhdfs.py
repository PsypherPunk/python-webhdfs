#!/usr/bin/env python

import sys
import json
import logging
import requests

LOGGING_FORMAT="[%(asctime)s] %(levelname)s: %(message)s"
logging.basicConfig( format=LOGGING_FORMAT, level=logging.WARNING )
logger = logging.getLogger( "webhdfs" )

class API():
	def __init__( self, prefix="http://localhost:14000/webhdfs/v1", verbose=False, user="hadoop" ):
		self.verbose = verbose
		self.prefix = prefix
		self.user = user

	def _get( self, path="/", op="GETFILESTATUS", stream=False ):
		url = "%s%s?user.name=%s&op=%s" % ( self.prefix, path, self.user, op )
		r = requests.get( url, stream=stream )
		return r

	def _post( self, path, file=None, data=None, op="CREATE" ):
		url = "%s%s?user.name=%s&op=%s&data=true" % ( self.prefix, path, self.user, op )
		headers = { "content-type": "application/octet-stream" }
		if file is not None:
			with open( file, "rb" ) as f:
				r = requests.put( url, headers=headers, data=f )
		else:
			r = requests.put( url, headers=headers, data=data )
		return r

	def _delete( self, path, recursive=False ):
		url = "%s%s?user.name=%s&op=DELETE&recursive=%s" % ( self.prefix, path, self.user, str( recursive ).lower() )
		r = requests.delete( url )
		return r

	def list( self, path ):
		r = self._get( path=path, op="LISTSTATUS" )
		return json.loads( r.text )

	def open( self, path ):
		r = self._get( path=path, op="OPEN" )
		return r.content

	def openstream( self, path ):
		return self._get( path=path, op="OPEN", stream=True )

	def exists( self, path ):
		r = self._get( path=path )
		j = json.loads( r.text )
		return j.has_key( "FileStatus" )

	def isdir( self, path ):
		r = self._get( path=path )
		j = json.loads( r.text )
		return ( self.exists( path ) and j[ "FileStatus" ][ "type" ] == "DIRECTORY" )

	def download( self, path, output=sys.stdout ):
		r = self.openstream( path )
		with open( output, "wb" ) as o:
			for chunk in r.iter_content( chunk_size=4096 ):
				if chunk:
					o.write( chunk )
					o.flush()

	def getmerge( self, path, output=sys.stdout ):
		"""Merges one or more HDFS files into a single, local file."""
		if self.isdir( path ) and not path.endswith( "/" ):
			path = "%s/" % path
		j = self.list( path )
		for file in j[ "FileStatuses" ][ "FileStatus" ]:
			r = self.openstream( path + file[ "pathSuffix" ] )
			for chunk in r.iter_content( chunk_size=4096 ):
				if chunk:
					output.write( chunk )
					output.flush()

	def create( self, path, file=None, data=None ):
		if ( file is None and data is None ) or ( file is not None and data is not None ):
			logger.warning( "Need either input file or data." )
		else:
			if file is not None:
				r = self._post( path, file=file )
			else:
				r = self._post( path, data=data )
			return r

	def delete( self, path, recursive=False ):
		if not self.exists( path ):
			logger.error( "Does not exist: %s" % path )
		else:
			r = self._delete( path, recursive=recursive )
			return json.loads( r.text )

	def checksum( self, path ):
		r = self._get( path=path, op="GETFILECHECKSUM" )
		return json.loads( r.text )

