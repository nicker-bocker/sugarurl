from __future__ import annotations

import abc
import re
from typing import Any
from typing import Dict
from typing import Iterable
from typing import Optional
from typing import Set
from typing import Tuple
from typing import Union
from urllib import parse
import collections.abc

class _Unset:
    __slots__ = ()

    def __bool__(self):
        return False

    def __repr__(self):
        return '_UNSET'


# sentinel
_UNSET = _Unset()


def _unset_default(value, default):
    if value is _UNSET:
        return default
    return value


class UrlLike(abc.ABC):
    @abc.abstractmethod
    def __str__(self):
        """Must override __str__ in subclass"""


class Url(UrlLike):
    # TODO add docstrings
    __slots__ = (
        '_params', '_trailing_slash', '_username', '_password',
        '_fragment', '_scheme', '_netloc', '_path', '_hostname',
        '_port', '_allow_fragments', '_url_string', '_hash'
    )
    parse = parse
    default_scheme = 'https'
    _RE_PATH_VALIDATOR = re.compile(r'^(/[^/\s]+/?)+$')
    _RE_NETLOC = re.compile(r"""
        (?:(?P<username>[^:]+):?(?P<password>.*)@)? # username and password optional
        (?P<hostname>[^:]+)                         # hostname mandatory
        (?::(?P<port>\d+))?                         # port optional
        """, re.VERBOSE)

    @classmethod
    def as_localhost(cls, **kwargs) -> Url:
        return cls('http://localhost', **kwargs)

    @classmethod
    def as_localhost_ssl(cls, **kwargs) -> Url:
        return cls('https://localhost', **kwargs)

    @classmethod
    def as_base(cls, url, **kwargs) -> Url:
        return cls(url).base_url(**kwargs)

    @classmethod
    def url_set(cls, urls: Iterable) -> Set[Url]:
        return {cls(url) for url in urls}

    def __init__(self,
                 base_url: Optional[Union[UrlLike, str]] = _UNSET, *,
                 scheme: Optional[str] = _UNSET,
                 hostname: Optional[str] = _UNSET,
                 netloc: Optional[str] = _UNSET,
                 path: Optional[Union[str, Iterable]] = _UNSET,
                 params: Optional[Dict[str, Any]] = _UNSET,
                 port: Optional[Union[int, str]] = _UNSET,
                 username: Optional[str] = _UNSET,
                 password: Optional[str] = _UNSET,
                 fragment: Optional[str] = _UNSET,
                 trailing_slash: bool = False,
                 allow_fragments: bool = True,
                 **kwargs
                 ):
        """Url

        :param base_url:
        :param scheme:
        :param hostname: 
        :param netloc:
        :param path:
        :param params:
        :param port:
        :param username:
        :param password:
        :param fragment:
        :param trailing_slash:
        :param allow_fragments:
        :param kwargs:
        """
        url_attrs = {}
        if base_url:
            # only positional arg could be string or Url
            if isinstance(base_url, Url):
                # remove the leading underscore from the attr names
                url_attrs = {k[1:]: getattr(base_url, k, None) for k in self.__slots__}
            else:
                split_tuple = self.parse.urlsplit(str(base_url), allow_fragments=allow_fragments)
                url_attrs = split_tuple._asdict()
                for attr in ['username', 'password', 'hostname', 'port']:
                    url_attrs[attr] = getattr(split_tuple, attr)
        if params is _UNSET:
            self._params = (
                url_attrs.get('params') or
                dict(self.parse.parse_qsl(url_attrs.get('query') or ''))
            )
        else:
            self._params = params
        self._params = self._params or {}
        self._trailing_slash = trailing_slash or url_attrs.get('trailing_slash')
        self._username = username or url_attrs.get('username')
        self._password = password or url_attrs.get('password')
        self._fragment = _unset_default(fragment, url_attrs.get('fragment'))
        self._scheme = scheme or url_attrs.get('scheme')
        self._netloc = netloc or url_attrs.get('netloc')
        self._path = _unset_default(path, url_attrs.get('path')) or ''
        self._hostname = hostname or url_attrs.get('hostname')
        self._port = _unset_default(port, url_attrs.get('port'))
        self._allow_fragments = allow_fragments
        args = [self._netloc, self._username, self._password, self._hostname, self._port]
        if any(args):
            self._netloc = self._parse_netloc(*args)
        if self._path:
            if isinstance(self._path, Iterable) and not isinstance(self._path, str):
                path_args = [x for i in map(str, self._path) for x in i.split('/') if x]
                self._path = '/'.join(path_args)
            if not self._path.startswith('/'):
                self._path = f"/{self._path}"
            if trailing_slash and not path.endswith('/'):
                self._path = f"{self._path}/"
            if not self._RE_PATH_VALIDATOR.match(self._path):
                raise ValueError(f'{self._path} is not a valid path')
        if self._netloc and not self._scheme:
            self._scheme = self.default_scheme
        s = self._url_string = self.parse.urlunsplit(
            (self.scheme, self.netloc, self.path, self.query, self.fragment))
        if isinstance(s, bytes) or not s:
            raise ValueError(f'{self!r} cannot formulate url.')

    def __str__(self):
        return self._url_string

    def __repr__(self):
        # return str(self)
        name = type(self).__name__
        args = (f'scheme={self.scheme},'
                f'netloc={self.netloc},'
                f'path={self.path or None},'
                f'query={self.query_unquote or None},'
                f'fragment={self.fragment or None}')
        return f'{name}({args})'

    def __call__(self, join_url=None, **kwargs) -> Url:
        if join_url:
            new_url = self.urljoin(
                join_url,
                allow_fragments=kwargs.get('allow_fragments', _UNSET),
                **kwargs
            )
        else:
            new_url = Url(self, **kwargs)
        return new_url

    def __hash__(self):
        try:
            return self._hash
        except AttributeError:
            s = self.parse.urlunsplit(
                (self.scheme, self.netloc, self.path, self.sorted_query, self.fragment))
            self._hash = hash(s)
            return self._hash

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            other = type(self)(other)
        return hash(self) == hash(other)
        # conditions = (
        #     self._path == other._path and
        #     self._params == other._params and
        #     self._hostname == other._hostname and
        #     self._fragment == other._fragment and
        #     self._scheme == other._scheme and
        #     self._username == other._username and
        #     self._password == other._password
        # )

    def __and__(self, params_dict):
        new_url = Url(self, params=params_dict)
        return new_url

    def __truediv__(self, endpoint):
        # if not isinstance(endpoint, (str. Iterable[str])):
        #     raise NotImplementedError('Only strings can be used with overloaded truediv operator')
        if isinstance(endpoint, Iterable) and not isinstance(endpoint, str):
            endpoint = list(endpoint)
        else:
            endpoint = [endpoint]
        path = [self._path] + endpoint
        new_url = Url(self, path=path)
        return new_url

    def __add__(self, join_url):
        return self(join_url=join_url)

    @property
    def scheme(self) -> str:
        return self._scheme

    @property
    def netloc(self) -> str:
        return self._netloc

    @property
    def path(self) -> str:
        return self._path

    @property
    def query(self) -> str:
        return self.parse.urlencode(self._params)

    @property
    def sorted_query(self) -> str:
        return self.parse.urlencode(dict(sorted(self._params.items())))

    @property
    def query_unquote(self) -> str:
        return self.parse.unquote(self.query)

    @property
    def fragment(self) -> str:
        return self._fragment

    @property
    def username(self) -> str:
        return self._username

    @property
    def password(self) -> str:
        return self._password

    @property
    def hostname(self):
        return self._hostname

    @property
    def port(self) -> int:
        return self._port

    @property
    def params(self) -> dict:
        return self._params.copy()

    @property
    def base_url(self) -> Url:
        try:
            return self._base_url
        except AttributeError:
            self._base_url = Url(scheme=self.scheme, netloc=self.netloc, port=self.port)
            return self._base_url

    @property
    def url(self) -> str:
        return str(self)

    def copy(self) -> Url:
        return Url(self)

    def sorted_params(self, **kwargs):
        params = dict(sorted(self.params.items()))
        new_url = Url(self, params=params, **kwargs)
        return new_url

    def modparams(self, __dict=None, /, **params) -> Url:
        __dict = __dict or {}
        new_url = Url(self, params={**self.params, **__dict, **params})
        return new_url

    def modpath(self, index, value, **kwargs) -> Url:
        old_path = self.path
        parts = [p for p in old_path.split('/') if p]
        if not 0 <= index <= len(parts):
            raise IndexError(f'{index} is out of range')
        if index == len(parts):
            parts = parts + [str(value)]
        else:
            parts[index] = str(value)
        new_path = f"/{'/'.join(parts)}{'/' if self._trailing_slash else ''}"
        new_url = Url(self, path=new_path, **kwargs)
        return new_url

    def urljoin(self, url, allow_fragments=_UNSET, **kwargs) -> Url:
        if allow_fragments is _UNSET:
            allow_fragments = self._allow_fragments
        new_url = Url(self.parse.urljoin(str(self), str(url), allow_fragments), **kwargs)
        return new_url

    def urldefrag(self) -> Tuple[Url, str]:
        url, frag = self.parse.urldefrag(str(self))
        return (Url(url), frag)

    def defrag(self, **kwargs) -> Url:
        new_url = Url(self, fragment=None, **kwargs)
        return new_url

    def depath(self, **kwargs) -> Url:
        new_url = Url(self, path=None, **kwargs)
        return new_url

    def deport(self, **kwargs) -> Url:
        new_url = Url(self, port=None, **kwargs)
        return new_url

    def deparam(self, **kwargs) -> Url:
        new_url = Url(self, params=None, **kwargs)
        return new_url

    def _parse_netloc(self, netloc, username, password, hostname, port):
        try:
            d = self._RE_NETLOC.match(netloc).groupdict()
        except Exception:
            d = {}
        username = username or d.get('username')
        password = password or d.get('password')
        hostname = hostname or d.get('hostname')
        port = port or d.get('port')
        res = ''
        if username and password:
            res += f"{username}:{password}@"
            self._username = username
            self._password = password
        try:
            res += hostname
            self._hostname = hostname
        except TypeError:
            return None
        if port:
            res += f":{port}"
            self._port = port
        return res
