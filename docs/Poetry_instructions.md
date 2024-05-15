# Poetry

- Install **pipx**: `sudp apt -y install pipx`

- Install **Poetry**: `pipx install poetry`

- Create new Python project with **Poetry**: `poetry new --src <project-name>`

- If working from a remote terminal, add the snippet of bash below to your .bashrc file in order to unlock your key ring over ssh. Poetry needs this to add packages to the project's toml file.

``` bash
function unlock_keyring ()
{
  read -rsp "Password: " pass
  export $(echo -n "${pass}" | gnome-keyring-daemon --replace --unlock)
  unset pass
}
```
