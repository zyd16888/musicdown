import json
import base64
from typing import Dict, List, Optional, Union
from decryptor import qrc_decrypt
from utils.enum import QrcType, SearchType

class MusicDataParser:
    """音乐数据解析器"""
    
    @staticmethod
    def parse_search_result(json_data: Dict, search_type: SearchType) -> Dict:
        """解析搜索结果数据
        
        Args:
            json_data (Dict): 搜索结果的原始JSON数据
            
        Returns:
            Dict: 解析后的搜索结果，包含歌曲列表等信息
        """
        try:
            match search_type:
                case SearchType.SONG:
                    result = {
                        'code': json_data.get('code', -1),
                        'songs': []
                    }
                    
                    if 'req_0' in json_data and 'data' in json_data['req_0']:
                        song_list = json_data['req_0']['data']['body']['song']['list']
                        for song in song_list:
                            song_info = {
                                'id': song.get('id', ''),
                                'mid': song.get('mid', ''),
                                'name': song.get('name', ''),
                                'singer': [{
                                    'id': s.get('id', ''),
                                    'mid': s.get('mid', ''),
                                    'name': s.get('name', '')
                                } for s in song.get('singer', [])],
                                'album': {
                                    'id': song['album'].get('id', ''),
                                    'mid': song['album'].get('mid', ''),
                                    'name': song['album'].get('name', '')
                                },
                                'interval': song.get('interval', 0)
                            }
                            result['songs'].append(song_info)
                case SearchType.ALBUM:
                    result = {
                        'code': json_data.get('code', -1),
                        'albums': []
                    }
                    
                    if 'req_0' in json_data and 'data' in json_data['req_0']:
                        album_list = json_data['req_0']['data']['body']['album']['list']
                        for album in album_list:
                            album_info = {
                                'albumID': album.get('albumID', ''),
                                'albumMID': album.get('albumMID', ''),
                                'albumName': album.get('albumName', ''),
                                'albumPic': album.get('albumPic', ''),
                                'publicTime': album.get('publicTime', ''),
                                'singerID': album.get('singerID', ''),
                                'singerMID': album.get('singerMID', ''),
                                'singerName': album.get('singerName', ''),
                                'song_count': album.get('song_count', 0)
                            }
                            result['albums'].append(album_info)
                case SearchType.SONGLIST:
                    result = {
                        'code': json_data.get('code', -1),
                        'playlists': []
                    }
                    
                    if 'req_0' in json_data and 'data' in json_data['req_0']:
                        playlist_list = json_data['req_0']['data']['body']['songlist']['list']
                        for playlist in playlist_list:
                            creator = playlist.get('creator', {})
                            playlist_info = {
                                'dissid': playlist.get('dissid', ''),
                                'dissname': playlist.get('dissname', ''),
                                'imgurl': playlist.get('imgurl', ''),
                                'introduction': playlist.get('introduction', ''),
                                'listennum': playlist.get('listennum', 0),
                                'song_count': playlist.get('song_count', 0),
                                'creator': {
                                    'name': creator.get('name', ''),
                                    'qq': creator.get('qq', 0),
                                    'isVip': creator.get('isVip', 0)
                                },
                                'createtime': playlist.get('createtime', '')
                            }
                            result['playlists'].append(playlist_info)
            return result
        except Exception as e:
            return {'code': -1, 'error': str(e)}

    @staticmethod
    def parse_lyrics(json_data: Dict) -> Dict:
        """解析普通歌词数据
        
        Args:
            json_data (Dict): 歌词的原始JSON数据
            
        Returns:
            Dict: 解析后的歌词数据，包含LRC格式的歌词文本
        """
        try:
            result = {
                'code': json_data.get('code', -1),
                'lyric': '',
                'trans': ''
            }
            
            if 'lyric' in json_data:
                # Base64解码
                lyric_bytes = base64.b64decode(json_data['lyric'])
                result['lyric'] = lyric_bytes.decode('utf-8')
            
            if 'trans' in json_data and json_data['trans']:
                trans_bytes = base64.b64decode(json_data['trans'])
                result['trans'] = trans_bytes.decode('utf-8')
            
            return result
        except Exception as e:
            return {'code': -1, 'error': str(e)}

    @staticmethod
    def parse_song_url(json_data: Dict) -> Dict:
        """解析歌曲下载链接
        
        Args:
            json_data (Dict): 歌曲URL的原始JSON数据
            
        Returns:
            Dict: 解析后的歌曲URL数据，包含下载链接
        """
        try:
            result = {
                'code': json_data.get('code', -1),
                'url': ''
            }
            
            if 'req_1' in json_data and 'data' in json_data['req_1']:
                data = json_data['req_1']['data']
                
                # 获取服务器地址列表和文件路径
                sip_list = data.get('sip', [])
                if not sip_list:
                    return {'code': -1, 'error': '未找到服务器地址'}
                    
                midurlinfo = data.get('midurlinfo', [])
                if not midurlinfo or not midurlinfo[0].get('purl'):
                    return {'code': -1, 'error': '未找到文件路径'}
                    
                # 使用第一个服务器地址
                base_url = sip_list[0]
                purl = midurlinfo[0]['purl']
                
                # 构建完整URL并将http转换为https
                full_url = base_url + purl
                if full_url.startswith('http://'):
                    full_url = 'https://' + full_url[7:]
                    
                result['url'] = full_url
                
            return result
        except Exception as e:
            return {'code': -1, 'error': str(e)}

    @staticmethod
    def parse_word_by_word_lyrics(json_data: Dict) -> Dict:
        """解析逐字歌词数据
        
        Args:
            json_data (Dict): 逐字歌词的原始JSON数据
            
        Returns:
            Dict: 解析后的逐字歌词数据，包含解密后的歌词文本
        """
        try:
            result = {
                'code': json_data.get('code', -1),
                'lyric': '',
                'trans': '',
                'roma': ''
            }
            
            if 'music.musichallSong.PlayLyricInfo.GetPlayLyricInfo' in json_data:
                data = json_data['music.musichallSong.PlayLyricInfo.GetPlayLyricInfo']['data']
                
                # 解密原文歌词
                if 'lyric' in data:
                    encrypted_lyric = data['lyric']
                    result['lyric'] = qrc_decrypt(encrypted_lyric, QrcType.CLOUD)
                
                # 解密翻译歌词
                if 'trans' in data and data['trans']:
                    encrypted_trans = data['trans']
                    result['trans'] = qrc_decrypt(encrypted_trans, QrcType.CLOUD)
                
                # 解密罗马音歌词
                if 'roma' in data and data['roma']:
                    encrypted_roma = data['roma']
                    result['roma'] = qrc_decrypt(encrypted_roma, QrcType.CLOUD)
            
            return result
        except Exception as e:
            return {'code': -1, 'error': str(e)}

    @staticmethod
    def parse_playlist(json_data: Dict) -> Dict:
        """解析歌单数据
        
        Args:
            json_data (Dict): 歌单的原始JSON数据
            
        Returns:
            Dict: 解析后的歌单数据，包含歌单信息和歌曲列表
        """
        try:
            result = {
                'code': json_data.get('code', -1),
                'id': '',
                'name': '',
                'desc': '',
                'picurl': '',
                'total_song_num': 0,
                'songs': []
                
            }
            
            if 'req_0' in json_data and 'data' in json_data['req_0']:
                playlist_data = json_data['req_0']['data']
                result.update({
                    'id': playlist_data.get('dirinfo', '').get('id', ''),
                    'name': playlist_data.get('dirinfo', '').get('title', ''),
                    'desc': playlist_data.get('dirinfo', '').get('desc', ''),
                    'picurl': playlist_data.get('dirinfo', '').get('picurl', ''),
                })
                
                # 解析歌曲列表
                if 'songlist' in playlist_data:
                    for song in playlist_data['songlist']:
                        song_info = {
                            'id': song.get('id', ''),
                            'mid': song.get('mid', ''),
                            'name': song.get('name', ''),
                            'singer': [{
                                'id': s.get('id', ''),
                                'mid': s.get('mid', ''),
                                'name': s.get('name', '')
                            } for s in song.get('singer', [])],
                            'album': {
                                'id': song['album'].get('id', ''),
                                'mid': song['album'].get('mid', ''),
                                'name': song['album'].get('name', '')
                            }
                        }
                        result['songs'].append(song_info)
            
            return result
        except Exception as e:
            return {'code': -1, 'error': str(e)}

    @staticmethod
    def parse_album(json_data: Dict) -> Dict:
        """解析专辑数据
        
        Args:
            json_data (Dict): 专辑的原始JSON数据
            
        Returns:
            Dict: 解析后的专辑数据，包含专辑信息和歌曲列表
        """
        try:
            result = {
                'code': json_data.get('code', -1),
                'albumMid': '',
                'totalNum': 0,
                'songList': []
            }
            
            if 'req_0' in json_data and 'data' in json_data['req_0']:
                album_data = json_data['req_0']['data']
                result['albumMid'] = album_data.get('albumMid', '')
                result['totalNum'] = album_data.get('totalNum', 0)
                
                # 解析歌曲列表
                if 'songList' in album_data:
                    for song in album_data['songList']:
                        songInfo = song['songInfo']

                        song_info = {
                            'id': songInfo.get('id', ''),
                            'mid': songInfo.get('mid', ''),
                            'name': songInfo.get('name', ''),
                            'singer': [{
                                'id': s.get('id', ''),
                                'mid': s.get('mid', ''),
                                'name': s.get('name', '')
                            } for s in songInfo.get('singer', [])],
                            'interval': songInfo.get('interval', 0)
                        }
                        result['songList'].append(song_info)
            
            return result
        except Exception as e:
            return {'code': -1, 'error': str(e)} 