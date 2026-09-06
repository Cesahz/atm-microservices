from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash

# ejemplo de uso check_password_hash(socio['password'], datos['password']):
# ejemplo de uso create_access_token(identity=datos['email'])

app = Flask(__name__)

app.config['JWT_SECRET_KEY'] = 'clave-secreta-super-segura'  # Cambiar en producción
jwt = JWTManager(app)



socios = {
    "juan@example.com": {"id": 1,"email": "juan@example.com","password": generate_password_hash("password123")},
    "ana@example.com": {"id": 2,"email": "ana@example.com","password": generate_password_hash("anaPass456")},
    "carlos@example.com": {"id": 3,"email": "carlos@example.com","password": generate_password_hash("c4rl0sPwd")}
    }


@app.route('/registro', methods=['POST'])
def registro():
    datos = request.json
    if 'email' not in datos or 'password' not in datos:
        return jsonify({"error": "Se requiere email y password"}), 400
    
    if datos['email'] in socios:
        return jsonify({"error": "El email ya está registrado"}), 400
    
    id_socio = len(socios) + 1
    socios[datos['email']] = {
        'id': id_socio,
        'email': datos['email'],
        'password': generate_password_hash(datos['password'])
    }
    return jsonify({"mensaje": "Socio registrado exitosamente", "id": id_socio}), 201

# DEFINIR RUTA '/login' CON MÉTODO POST:
#     FUNCIÓN login():
#         OBTENER datos del cuerpo de la solicitud
#         SI 'email' o 'password' no están en los datos:
#             RETORNAR error 400
#         BUSCAR socio por email
#         SI no se encuentra el socio o la contraseña no coincide:
#             RETORNAR error 401
#         CREAR token de acceso con el email como identidad
#         RETORNAR token de acceso


@app.route('/socios/perfil', methods=['GET'])
@jwt_required()
def obtener_perfil():
    email_actual = get_jwt_identity()
    socio = socios.get(email_actual)
    if socio:
        return jsonify({
            "id": socio['id'],
            "email": socio['email']
        }), 200
    return jsonify({"error": "Socio no encontrado"}), 404


@app.route('/socios/actualizar', methods=['PUT'])
@jwt_required()
def actualizar_socio():
    email_actual = get_jwt_identity()
    datos = request.json
    if email_actual in socios:
        socio = socios[email_actual]
        socio.update(datos)
        return jsonify({"mensaje": "Información actualizada correctamente"}), 200
    return jsonify({"error": "Socio no encontrado"}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5002)