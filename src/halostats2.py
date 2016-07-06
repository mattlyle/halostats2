#!/usr/bin/env python

import datetime
import hashlib
import json
import os
import sys
import traceback
import urllib2

CACHE_PATH = 'cached-data'

API_KEY_PATH = 'api-key.txt'
GAMERTAGS_PATH = 'gamertags.txt'

FULL_MATCH_DOWNLOAD_SET_SIZE = 25

API_KEY = ''

def main( ):
	# load the API key
	global API_KEY
	file_in = open( API_KEY_PATH, 'r' )
	API_KEY = file_in.read( ).strip( )
	file_in.close( )

	# load the gamertags
	file_in = open( GAMERTAGS_PATH, 'r' )
	gamertags = file_in.read( ).strip( ).splitlines( )
	file_in.close( )

	gamertags_combined = ''
	for gamertag in gamertags:

		if len( gamertags_combined ) > 0:
			gamertags_combined += ','
		gamertags_combined += gamertag

	try:

		print 'Loading Metadata: Maps...'
		maps = load_metadata_item( 'maps' )

		print 'Loading Metadata: Game Based Variants...'
		game_base_variants = load_metadata_item( 'game-base-variants' )

		print 'Loading Warzone matches...'
		for gamertag in gamertags:
			print '  %s' % gamertag
			display_match_stats( maps, game_base_variants, gamertag )

	except Exception:
		traceback.print_exc( )

	print 'done.'

def run_api_command( uri, cacheable ):
	md5sum = hashlib.md5( )
	md5sum.update( uri )

	cache_filename = None
	if cacheable:
		cache_filename = '%s/%s.json' % (CACHE_PATH, md5sum.hexdigest( ))

	if cacheable and os.path.isfile( cache_filename ):
		file_in = open( cache_filename, 'r' )
		data = file_in.read( )
		file_in.close( )
	else:
		request = urllib2.Request( 'https://www.haloapi.com%s' % uri )
		request.add_header( 'Ocp-Apim-Subscription-Key', API_KEY )
		response = urllib2.urlopen( request )
		data = response.read( )

	parsed = json.loads( data )

	if cacheable:
		if not os.path.isdir( CACHE_PATH ):
			os.mkdir( CACHE_PATH )
		file_out = open( cache_filename, 'w' )
		file_out.write( data )
		file_out.close( )

	return parsed, cache_filename

def load_metadata_item( item_name ):
	(raw, cache_filename) = run_api_command( '/metadata/h5/metadata/%s' % item_name, True )

	lookup_table = { }
	for entry in raw:
		# print '%s %s' % ( entry[ 'id' ], entry[ 'name' ] )
		lookup_table[ entry[ 'id' ] ] = entry

	return lookup_table

def load_player_matches( gamertag ):
	matches = [ ]

	start = 0
	while True:
		(partial_set, cache_filename) = run_api_command( '/stats/h5/players/%s/matches?start=%d' % (gamertag, start), True )
		for match in partial_set[ 'Results' ]:
			matches.append( match )

		if len( partial_set[ 'Results' ] ) != FULL_MATCH_DOWNLOAD_SET_SIZE:
			os.remove( cache_filename )
			return matches

		start += FULL_MATCH_DOWNLOAD_SET_SIZE

def display_match_stats( maps, game_base_variants, gamertag ):
	matches = load_player_matches( gamertag )

	stats = { }

	for match in matches:

		if match[ 'MapId' ] not in maps:
			print 'Unknown map: %s' % match[ 'MapId' ]
			sys.exit( 1 )
		match_map = maps[ match[ 'MapId' ] ]

		if match[ 'GameBaseVariantId' ] not in game_base_variants:
			print 'Unknown game based variant: %s' % match[ 'GameBaseVariantId' ]
			sys.exit( 1 )
		match_game_base_variant = game_base_variants[ match[ 'GameBaseVariantId' ] ]

		if match_game_base_variant[ 'internalName' ] == 'WarzonePvE':

			match_date = match[ 'MatchCompletedDate' ][ 'ISO8601Date' ]

			parsed_match_date = datetime.datetime.strptime( match_date, '%Y-%m-%dT%H:%M:%SZ' )

			game_base_variant_name = match_game_base_variant[ 'name' ]

			if parsed_match_date < datetime.datetime( 2016, 6, 1 ):
				game_base_variant_name += ' Beta'

			if game_base_variant_name not in stats:
				stats[ game_base_variant_name ] = { }

			if match_map[ 'name' ] not in stats[ game_base_variant_name ]:
				stats[ game_base_variant_name ][ match_map[ 'name' ] ] = [ 0, 0 ]

			for player in match[ 'Players' ]:
				if player[ 'Player' ][ 'Gamertag' ].lower( ) == gamertag.lower( ):
					# print '%d %d' % ( player[ 'Rank' ], player[ 'Result' ] )
					if player[ 'Result' ] == 1:
						# loss
						stats[ game_base_variant_name ][ match_map[ 'name' ] ][ 1 ] += 1
					elif player[ 'Result' ] == 3:
						# win
						stats[ game_base_variant_name ][ match_map[ 'name' ] ][ 0 ] += 1

	for game_base_variant_name in sorted( stats ):

		total_wins = 0
		total_losses = 0

		print '    %s:' % game_base_variant_name
		for map_name in sorted( stats[ game_base_variant_name ] ):
			wins = stats[ game_base_variant_name ][ map_name ][ 0 ]
			losses = stats[ game_base_variant_name ][ map_name ][ 1 ]
			print '        %-24s W:%3d  /  L:%3d = %6.2f%%' % (map_name, wins, losses, 100.0 * wins / (wins + losses))

			total_wins += wins
			total_losses += losses

		print '        %-24s W:%3d  /  L:%3d = %6.2f%%' % ('Total', total_wins, total_losses, 100.0 * total_wins / (total_wins + total_losses))

	return

if __name__ == "__main__":
	main( )
